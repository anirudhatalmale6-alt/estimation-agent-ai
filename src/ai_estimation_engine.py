"""
AI-powered estimation engine.
Uses Azure OpenAI to reason about project complexity and intelligently
adjust PERF activity units beyond simple rule-based defaults.
"""

import os
import yaml
from .azure_openai_client import AzureOpenAIClient


ESTIMATION_PROMPT = """You are a senior performance engineer with 15+ years of experience estimating performance testing effort for enterprise billing and middleware systems.

Given the project analysis below, calculate the PERF estimation by:
1. Classifying project size (small/medium/large)
2. Setting units for each of the 11 PERF activities
3. Adjusting units based on architecture complexity, risk factors, and integrations
4. Applying the 19% efficiency factor
5. Calculating total person-days and cost

PERF Activities and Base Times:
| Activity | Base Days | Default Complexity | Multiplier |
|----------|-----------|-------------------|------------|
| Analysis | 1.50 | medium | 1.0x |
| Assessment | 1.50 | medium | 1.0x |
| Batch Job Execution | 1.50 | medium | 1.0x |
| Data Prep | 0.88 | medium | 1.0x |
| Defects Management | 4.01 | medium | 1.0x |
| Execution - Peak Load | 1.76 | peak_load | 1.0x |
| Execution - Stress Test | 1.76 | stress_test | 1.0x |
| HP PC Support | 1.00 | hp_pc_support | 1.0x |
| Planning | 3.01 | medium | 1.0x |
| Reporting | 2.51 | medium | 1.0x |
| Script Design | 2.00 | complex | 2.0x (= 4.00 days) |

Default Units by Size:
| Activity | Small | Medium | Large |
|----------|-------|--------|-------|
| Analysis | 1 | 2 | 3 |
| Assessment | 1 | 1 | 2 |
| Batch Job Execution | 1 | 2 | 3 |
| Data Prep | 1 | 1 | 2 |
| Defects Management | 1 | 2 | 3 |
| Execution - Peak Load | 1 | 2 | 3 |
| Execution - Stress Test | 1 | 1 | 2 |
| HP PC Support | 1 | 2 | 3 |
| Planning | 1 | 1 | 2 |
| Reporting | 1 | 2 | 3 |
| Script Design | 2 | 6 | 10 |

Return as JSON:
{
  "project_size": "small | medium | large",
  "size_reasoning": "why this size",
  "activities": [
    {
      "name": "Activity Name",
      "base_days": 0.00,
      "complexity": "string",
      "multiplier": 0.0,
      "exec_time_days": 0.00,
      "default_units": 0,
      "adjusted_units": 0,
      "adjustment_reason": "why units were changed from default (or 'default' if no change)",
      "total_days": 0.00
    }
  ],
  "totals": {
    "total_pd_before_efficiency": 0.00,
    "efficiency_percentage": 19,
    "efficiency_saving_pd": 0.00,
    "total_pd_after_efficiency": 0.00,
    "cost_per_pd": 250,
    "total_cost": 0.00
  },
  "ai_insights": [
    "key observations about this project's performance testing complexity"
  ],
  "risk_based_adjustments": [
    "specific adjustments made due to identified risks"
  ]
}"""


class AIEstimationEngine:
    def __init__(self, ai_client=None, config_path=None):
        self.ai = ai_client or AzureOpenAIClient()
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config", "estimation_rules.yaml"
            )
        with open(config_path) as f:
            self.rules = yaml.safe_load(f)

    def estimate(self, hld_analysis=None, nfr_data=None, pet_ticket_id=None):
        context_parts = []

        if hld_analysis:
            context_parts.append(f"HLD Analysis:\n{self._format_hld(hld_analysis)}")

        if nfr_data:
            context_parts.append(f"NFR Data from Meeting:\n{self._format_nfr(nfr_data)}")

        if pet_ticket_id:
            context_parts.append(f"PET Ticket: {pet_ticket_id}")

        if not context_parts:
            context_parts.append("No project data provided. Use medium project defaults.")

        result = self.ai.chat_json(
            system_prompt=ESTIMATION_PROMPT,
            user_prompt="\n\n".join(context_parts),
            max_tokens=3000
        )

        result["pet_ticket_id"] = pet_ticket_id
        return result

    def estimate_with_calibration(self, estimation_result, feedback):
        prompt = f"""The initial estimation was:
Total PD (after efficiency): {estimation_result['totals']['total_pd_after_efficiency']}
Cost: ${estimation_result['totals']['total_cost']:,.2f}

The performance manager provided this feedback:
{feedback}

Adjust the estimation based on this feedback. Show what changed and why.
Return the same JSON structure as before with updated values."""

        return self.ai.chat_json(
            system_prompt=ESTIMATION_PROMPT,
            user_prompt=prompt,
            max_tokens=3000
        )

    def format_report(self, estimation_result):
        pet_id = estimation_result.get("pet_ticket_id", "PET-XXX")
        size = estimation_result.get("project_size", "unknown").upper()
        activities = estimation_result.get("activities", [])
        totals = estimation_result.get("totals", {})
        insights = estimation_result.get("ai_insights", [])
        adjustments = estimation_result.get("risk_based_adjustments", [])

        lines = []
        lines.append("=" * 70)
        lines.append(f"  PERF ESTIMATION REPORT - {pet_id}")
        lines.append("  (AI-Powered Analysis)")
        lines.append("=" * 70)
        lines.append(f"  Project Size     : {size}")
        lines.append(f"  Size Reasoning   : {estimation_result.get('size_reasoning', '')}")
        lines.append(f"  Estimation Phase : +/- 10%")
        lines.append("")
        lines.append("-" * 70)
        lines.append(f"  {'PERF Activity':<28} {'Complexity':<12} {'Time(d)':<9} {'Units':<7} {'Total(d)'}")
        lines.append("-" * 70)

        for act in activities:
            lines.append(
                f"  {act['name']:<28} {act.get('complexity', 'medium'):<12} "
                f"{act.get('exec_time_days', 0):<9.2f} {act.get('adjusted_units', 0):<7} "
                f"{act.get('total_days', 0):.2f}"
            )

        lines.append("-" * 70)
        lines.append("")

        before = totals.get("total_pd_before_efficiency", 0)
        after = totals.get("total_pd_after_efficiency", 0)
        saving = totals.get("efficiency_saving_pd", 0)
        cost = totals.get("total_cost", 0)
        eff = totals.get("efficiency_percentage", 19)

        lines.append(f"  Vendor Effort GRAND TOTAL (Before Efficiency):")
        lines.append(f"    {before * 8:.2f} hrs = {before:.2f} PD")
        lines.append("")
        lines.append(f"  Vendor Effort GRAND TOTAL (After {eff}% Efficiency):")
        lines.append(f"    {after * 8:.2f} hrs = {after:.2f} PD")
        lines.append("")
        lines.append(f"  Saving due to Efficiency: {saving:.2f} PD")
        lines.append(f"  Cost @ $250/PD = ${cost:,.2f}")

        if insights:
            lines.append("")
            lines.append("  AI Insights:")
            for insight in insights:
                lines.append(f"    - {insight}")

        if adjustments:
            lines.append("")
            lines.append("  Risk-Based Adjustments:")
            for adj in adjustments:
                lines.append(f"    - {adj}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _format_hld(self, hld):
        parts = []
        parts.append(f"Project: {hld.get('project_name', 'Unknown')}")
        parts.append(f"Description: {hld.get('project_description', '')}")

        in_scope = hld.get("in_scope_items", [])
        if in_scope:
            parts.append(f"In-scope items ({len(in_scope)}):")
            for item in in_scope:
                name = item.get("name", item) if isinstance(item, dict) else item
                parts.append(f"  - {name}")

        use_cases = hld.get("use_cases", [])
        if use_cases:
            parts.append(f"Use cases ({len(use_cases)}):")
            for uc in use_cases:
                name = uc.get("name", uc) if isinstance(uc, dict) else uc
                parts.append(f"  - {name}")

        arch = hld.get("architecture", {})
        if arch:
            parts.append(f"Architecture: {arch.get('pattern', 'unknown')}")
            components = arch.get("components", [])
            parts.append(f"Components ({len(components)}): {', '.join(c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in components)}")

        integrations = hld.get("integrations", [])
        if integrations:
            parts.append(f"Integrations ({len(integrations)}): {', '.join(i.get('name', str(i)) if isinstance(i, dict) else str(i) for i in integrations)}")

        risks = hld.get("performance_risk_factors", [])
        if risks:
            parts.append(f"Risk factors ({len(risks)}):")
            for r in risks:
                if isinstance(r, dict):
                    parts.append(f"  - {r.get('factor', '')}: {r.get('reasoning', '')}")
                else:
                    parts.append(f"  - {r}")

        return "\n".join(parts)

    def _format_nfr(self, nfr):
        parts = []
        wp = nfr.get("workload_profile", {})
        if wp:
            parts.append(f"Concurrent users: {wp.get('concurrent_users_normal', 'TBD')} normal, {wp.get('concurrent_users_peak', 'TBD')} peak")
            parts.append(f"TPS: {wp.get('tps_normal', 'TBD')} normal, {wp.get('tps_peak', 'TBD')} peak")
            parts.append(f"Critical transactions: {', '.join(wp.get('critical_transactions', []))}")
            batch_jobs = wp.get("batch_jobs", [])
            if batch_jobs:
                for bj in batch_jobs:
                    parts.append(f"Batch: {bj.get('name', '')} - {bj.get('volume', '')} every {bj.get('frequency', '')} (SLA: {bj.get('sla', '')})")

        pt = nfr.get("performance_targets", {})
        if pt:
            parts.append(f"Response time: read {pt.get('response_time_read', 'TBD')}, write {pt.get('response_time_write', 'TBD')}")
            parts.append(f"Availability: {pt.get('availability_sla', 'TBD')}")
            parts.append(f"Error rate: {pt.get('error_rate_threshold', 'TBD')}")
            parts.append(f"CPU: {pt.get('cpu_threshold', 'TBD')}, Memory: {pt.get('memory_threshold', 'TBD')}")

        risks = nfr.get("risks", [])
        if risks:
            parts.append(f"Risks ({len(risks)}):")
            for r in risks:
                if isinstance(r, dict):
                    parts.append(f"  - {r.get('description', '')}")

        return "\n".join(parts)
