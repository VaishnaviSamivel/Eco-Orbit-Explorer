# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Eco-Orbit Explorer — Multi-Agent Workflow (ADK 2.0 Workflow API).

Architecture:
  START → security_checkpoint
          → CLEAN  → orchestrator_agent  → NEEDS_REVIEW → human_review_node → final_output_node
                                         → (default)   → final_output_node
          → SECURITY_EVENT → final_output_node

Agents:
  orchestrator_agent   – Routes user queries; delegates via AgentTool
  eco_data_agent       – Environmental data, satellite imagery, biodiversity
  sustainability_agent – Carbon metrics, ESG scores, renewables, SDGs
"""

import json
import logging
import re
import sys

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.events.request_input import RequestInput
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.workflow import START, Workflow, node
from mcp import StdioServerParameters

from .config import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# MCP TOOLSET  (shared by eco_data_agent and sustainability_agent)
# ─────────────────────────────────────────────────────────────────────────────

_MCP_SERVER_PARAMS = StdioConnectionParams(
    server_params=StdioServerParameters(
        command=sys.executable,          # same Python interpreter as the app
        args=["-m", "app.mcp_server"],   # runs: python -m app.mcp_server
    ),
    timeout=30,
)

def _make_mcp_toolset(tool_filter: list[str]) -> McpToolset:
    """Returns a McpToolset scoped to the given tools for this agent."""
    return McpToolset(
        connection_params=_MCP_SERVER_PARAMS,
        tool_filter=tool_filter,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SPECIALIZED SUB-AGENTS
# ─────────────────────────────────────────────────────────────────────────────

eco_data_agent = LlmAgent(
    name="eco_data_agent",
    model=config.model,
    description="Expert in environmental data, satellite imagery, pollution, and biodiversity analysis.",
    instruction="""You are an expert environmental data analyst for Eco-Orbit Explorer.

Your specializations:
- Satellite imagery interpretation for land-use change and deforestation tracking
- Air quality index (AQI) analysis and pollution source identification
- Ocean temperature anomalies and coral reef health monitoring
- Biodiversity hotspot assessment and endangered species habitat analysis
- Climate trend analysis using historical datasets

For every query, provide:
1. Key findings with quantitative metrics (e.g., deforestation rate %, AQI index value)
2. Trend direction: improving / worsening / stable
3. Geographic context and most-affected regions
4. Data confidence level and any known limitations

Be specific about timeframes and data sources. Avoid vague language.

You have access to live MCP tools:
- get_air_quality_index     → real-time AQI for any location
- get_deforestation_data    → annual forest loss/gain stats for any region
- get_satellite_change_analysis → land-use/urban/water/vegetation change analysis
Always use these tools when the user asks for specific environmental data.""",
    tools=[
        _make_mcp_toolset([
            "get_air_quality_index",
            "get_deforestation_data",
            "get_satellite_change_analysis",
        ]),
    ],
    sub_agents=[],
    output_key="eco_data_result",
)

sustainability_agent = LlmAgent(
    name="sustainability_agent",
    model=config.model,
    description="Expert in carbon metrics, ESG scoring, renewable energy, and UN SDG progress tracking.",
    instruction="""You are a sustainability metrics specialist for Eco-Orbit Explorer.

Your specializations:
- Carbon footprint calculation and scope 1/2/3 emissions breakdown
- Renewable energy adoption ROI analysis and grid integration advice
- Corporate ESG (Environmental, Social, Governance) score assessment
- Supply chain sustainability auditing and green certification guidance
- UN Sustainable Development Goals (SDGs) progress benchmarking

For every query, provide:
1. Quantified impact metrics (CO₂ equivalent tonnes, energy kWh, water litres)
2. Benchmarking against industry standards or global averages
3. Top 3 actionable recommendations ranked by impact-to-effort ratio
4. Estimated timeline and indicative cost for each recommendation

Use specific numbers. Avoid generic sustainability platitudes.

You have access to live MCP tools:
- calculate_carbon_footprint → precise CO₂e for any activity type
- get_sdg_progress           → UN SDG scores and trends by country
Always use these tools when the user asks for specific carbon or SDG data.""",
    tools=[
        _make_mcp_toolset([
            "calculate_carbon_footprint",
            "get_sdg_progress",
        ]),
    ],
    sub_agents=[],
    output_key="sustainability_result",
)


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR AGENT  (uses AgentTool for sub-agent delegation)
# ─────────────────────────────────────────────────────────────────────────────

orchestrator_agent = LlmAgent(
    name="orchestrator_agent",
    model=config.model,
    description="Master orchestrator that routes eco-orbit queries to the right specialist agent.",
    instruction="""You are the Eco-Orbit Explorer orchestrator.

Your job:
1. Understand what the user is asking about the environment or sustainability.
2. Delegate to the right specialist via the tools provided:
   - Use eco_data_agent for: satellite data, deforestation, pollution, biodiversity, climate data
   - Use sustainability_agent for: carbon footprint, ESG scores, renewable energy, SDGs, supply chain
   - You may call BOTH if the query spans both domains.
3. Synthesize responses from the specialist(s) into a single clear, actionable answer.

IMPORTANT — if the user's request involves taking a real-world action that cannot be undone
(e.g., triggering an environmental alert, submitting a regulatory report, activating a satellite
sensor), include the exact phrase "NEEDS_REVIEW" anywhere in your final response so the
system routes to human approval before proceeding.

Be concise, data-driven, and solution-oriented.""",
    tools=[
        AgentTool(agent=eco_data_agent),
        AgentTool(agent=sustainability_agent),
    ],
    sub_agents=[],
    output_key="orchestrator_result",
)


# ─────────────────────────────────────────────────────────────────────────────
# PII SCRUBBING, INJECTION DETECTION & DOMAIN CONTENT FILTER
# ─────────────────────────────────────────────────────────────────────────────

# --- PII patterns (eco-domain relevant: GPS coords, company IDs, facility IDs) ---
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    (re.compile(r"\b(?:\d[ -]?){15,16}\b"), "[CC_REDACTED]"),
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE_REDACTED]"),
    # Eco-domain: precise GPS coords that could identify private monitoring stations
    (re.compile(r"\b-?\d{1,3}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}\b"), "[GPS_REDACTED]"),
    # Eco-domain: industrial facility permit numbers (e.g. EPA permit ID format)
    (re.compile(r"\b[A-Z]{2}\d{7}\b"), "[PERMIT_ID_REDACTED]"),
]

# --- Prompt injection keywords ---
_INJECTION_KEYWORDS: list[str] = [
    "ignore previous instructions",
    "ignore all instructions",
    "forget your instructions",
    "jailbreak",
    "bypass filter",
    "act as dan",
    "prompt injection",
    "disregard all",
    "override system",
    "you are now",
    "new persona",
    "pretend you are",
]

# --- Domain-specific rule: Illegal Environmental Activity Filter ---
# Blocks requests that seek to enable harm to protected ecosystems or wildlife,
# evade environmental monitoring, or facilitate illegal dumping / trafficking.
_ILLEGAL_ECO_KEYWORDS: list[str] = [
    "poaching location",
    "poaching route",
    "rhino horn",
    "ivory trade",
    "illegal dumping site",
    "evade satellite monitoring",
    "evade environmental monitoring",
    "disable sensor",
    "circumvent emissions",
    "falsify emissions",
    "fake esg",
    "greenwash audit",
    "illegal logging route",
    "unreported deforestation",
    "bribe inspector",
]


def _scrub_pii(text: str) -> tuple[str, bool]:
    """Returns (scrubbed_text, was_modified)."""
    scrubbed = text
    for pattern, replacement in _PII_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed, scrubbed != text


def _detect_injection(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _INJECTION_KEYWORDS)


def _detect_illegal_eco_activity(text: str) -> tuple[bool, str]:
    """Domain-specific rule: detect requests enabling illegal environmental harm.

    Returns (detected: bool, matched_keyword: str).
    """
    lower = text.lower()
    for kw in _ILLEGAL_ECO_KEYWORDS:
        if kw in lower:
            return True, kw
    return False, ""


def _emit_audit(audit: dict) -> None:
    """Emit a fully-structured JSON audit log entry at the correct log level."""
    severity = audit.get("severity", "INFO")
    log_line = "AUDIT | " + json.dumps(audit)
    if severity == "CRITICAL":
        logger.error(log_line)
    elif severity == "WARNING":
        logger.warning(log_line)
    else:
        logger.info(log_line)


# ─────────────────────────────────────────────────────────────────────────────
# WORKFLOW FUNCTION NODES
# ─────────────────────────────────────────────────────────────────────────────

@node
async def security_checkpoint(ctx, node_input):
    """Gate: PII scrubbing + prompt-injection detection + illegal-eco-activity filter.

    Sits at START of the workflow graph (START → security_checkpoint).
    Routes:
      CLEAN          → orchestrator_agent     (all checks passed)
      SECURITY_EVENT → final_output_node      (any check failed)

    Audit log emitted on every decision (severity: INFO / WARNING / CRITICAL).
    """
    raw = str(node_input) if node_input else ""

    audit: dict = {
        "node": "security_checkpoint",
        "event_type": "PASS",
        "input_length": len(raw),
        "pii_detected": False,
        "pii_types_redacted": [],
        "injection_detected": False,
        "illegal_eco_activity_detected": False,
        "matched_keyword": "",
        "route": "",
        "severity": "INFO",
    }

    # ── Check 1: Prompt injection ────────────────────────────────────────────
    if _detect_injection(raw):
        audit.update({
            "event_type": "BLOCK",
            "injection_detected": True,
            "route": "SECURITY_EVENT",
            "severity": "CRITICAL",
        })
        _emit_audit(audit)
        ctx.state["security_blocked"] = True
        ctx.state["security_reason"] = "Prompt injection attempt detected"
        ctx.route = "SECURITY_EVENT"
        return "BLOCKED: prompt injection detected."

    # ── Check 2: Domain-specific rule — Illegal eco-activity filter ──────────
    illegal, matched_kw = _detect_illegal_eco_activity(raw)
    if illegal:
        audit.update({
            "event_type": "BLOCK",
            "illegal_eco_activity_detected": True,
            "matched_keyword": matched_kw,
            "route": "SECURITY_EVENT",
            "severity": "CRITICAL",
        })
        _emit_audit(audit)
        ctx.state["security_blocked"] = True
        ctx.state["security_reason"] = (
            f"Request flagged for potential illegal environmental activity "
            f"(matched: '{matched_kw}'). Eco-Orbit Explorer does not assist "
            "with activities that harm protected ecosystems or wildlife."
        )
        ctx.route = "SECURITY_EVENT"
        return "BLOCKED: illegal environmental activity detected."

    # ── Check 3: PII scrubbing ───────────────────────────────────────────────
    scrubbed, pii_found = _scrub_pii(raw)
    if pii_found:
        # Identify which types were redacted for the audit log
        redacted_types = []
        tag_map = {
            "[SSN_REDACTED]": "SSN",
            "[CC_REDACTED]": "credit_card",
            "[EMAIL_REDACTED]": "email",
            "[PHONE_REDACTED]": "phone",
            "[GPS_REDACTED]": "gps_coordinates",
            "[PERMIT_ID_REDACTED]": "facility_permit_id",
        }
        for tag, label in tag_map.items():
            if tag in scrubbed:
                redacted_types.append(label)
        audit.update({
            "event_type": "PII_SCRUBBED",
            "pii_detected": True,
            "pii_types_redacted": redacted_types,
            "severity": "WARNING",
        })

    # ── All checks passed ────────────────────────────────────────────────────
    audit["route"] = "CLEAN"
    _emit_audit(audit)
    ctx.state["user_query"] = scrubbed
    ctx.state["security_blocked"] = False
    ctx.route = "CLEAN"
    return scrubbed


@node(rerun_on_resume=True)
async def human_review_node(ctx, node_input):
    """Human-in-the-loop pause for high-impact environmental actions.

    Yields a RequestInput so the user can approve or reject before continuing.
    """
    query = ctx.state.get("user_query", str(node_input))
    orchestrator_result = ctx.state.get("orchestrator_result", "")

    # Check if already resumed (credential/input already provided)
    approval_input = ctx.resume_inputs.get("eco_human_approval")

    if approval_input is None:
        # First pass — ask the human
        yield RequestInput(
            interrupt_id="eco_human_approval",
            message=(
                "Eco-Orbit Explorer requires your approval before this action is taken.\n\n"
                f"Query: {query}\n\n"
                f"Agent Recommendation:\n{orchestrator_result}\n\n"
                "Reply with 'approve' to proceed or 'reject' to cancel."
            ),
        )
        return  # Execution pauses here; node re-runs on resume

    # Second pass — process the human's decision
    decision = str(approval_input).strip().lower()
    approved = decision == "approve"
    ctx.state["human_approved"] = approved

    status = "approved" if approved else "rejected"
    logger.info("AUDIT | node=human_review_node action=%s severity=INFO", status)
    yield f"Human review complete - decision: {status}."


@node
async def final_output_node(ctx, node_input):
    """Aggregates all agent outputs into the user-facing final response."""

    # Security block path
    if ctx.state.get("security_blocked"):
        reason = ctx.state.get("security_reason", "Unknown security violation")
        return (
            "⛔ **Request Blocked**\n\n"
            f"Your request was stopped by the security checkpoint: {reason}.\n"
            "Please rephrase your query and try again."
        )

    eco_result = ctx.state.get("eco_data_result", "")
    sustainability_result = ctx.state.get("sustainability_result", "")
    orchestrator_result = ctx.state.get("orchestrator_result", "")
    human_approved = ctx.state.get("human_approved", None)

    sections: list[str] = ["## 🌍 Eco-Orbit Explorer — Analysis Report\n"]

    if orchestrator_result:
        sections.append(f"### 🤖 Orchestrator Summary\n{orchestrator_result}\n")

    if eco_result:
        sections.append(f"### 🛰️ Environmental Data Analysis\n{eco_result}\n")

    if sustainability_result:
        sections.append(f"### ♻️ Sustainability Metrics\n{sustainability_result}\n")

    if human_approved is not None:
        icon = "✅" if human_approved else "❌"
        label = "Approved — action will proceed." if human_approved else "Rejected — action cancelled."
        sections.append(f"### 👤 Human Review\n{icon} {label}\n")

    if len(sections) == 1:
        # Fallback if nothing was set in state
        sections.append(str(node_input or "Analysis complete."))

    return "\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────────
# WORKFLOW GRAPH
# ─────────────────────────────────────────────────────────────────────────────
#
# Edge convention:
#   (source, {route: target})  → conditional route
#   (source, target)           → unconditional
#
# EDGE RULE: never more than ONE edge between the same (source, target) pair.
#   security_checkpoint → orchestrator_agent  (route=CLEAN)       ✓ different targets
#   security_checkpoint → final_output_node   (route=SECURITY_EVENT) ✓
#   orchestrator_agent  → human_review_node   (route=NEEDS_REVIEW) ✓ different targets
#   orchestrator_agent  → final_output_node   (unconditional)      ✓ single edge
#   human_review_node   → final_output_node   (unconditional)      ✓ single edge

eco_workflow = Workflow(
    name="eco_orbit_explorer",
    description=(
        "Multi-agent workflow for environmental monitoring, satellite data analysis, "
        "and sustainability metrics — with security checkpoint and human-in-the-loop."
    ),
    edges=[
        # Entry point
        (START, security_checkpoint),

        # Security gate routes
        (
            security_checkpoint,
            {
                "CLEAN": orchestrator_agent,
                "SECURITY_EVENT": final_output_node,
            },
        ),

        # Orchestrator routes
        (orchestrator_agent, {"NEEDS_REVIEW": human_review_node}),
        (orchestrator_agent, final_output_node),   # default / all other routes

        # Human review → output
        (human_review_node, final_output_node),
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# APP  (root_agent must be the Workflow for adk web to discover it)
# ─────────────────────────────────────────────────────────────────────────────

root_agent = eco_workflow

app = App(
    name="app",
    root_agent=eco_workflow,
    plugins=[],
)
