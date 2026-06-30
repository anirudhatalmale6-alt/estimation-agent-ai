"""
AI-powered test plan content writer.
Uses Azure OpenAI to generate intelligent, context-aware test plan sections
rather than template-based content. Outputs to PDF via reportlab.
"""

import os
from datetime import date
from .azure_openai_client import AzureOpenAIClient
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)


TEST_PLAN_PROMPT = """You are a senior performance engineer writing a Performance Test Plan for an enterprise project. Given the project context below, generate the content for each section.

Return as JSON with these keys (each value is a string with the section content):
{
  "introduction_purpose": "2-3 sentences about the plan's purpose, referencing the specific project",
  "introduction_background": "2-3 sentences about the project background from the HLD",
  "scope_in_scope": ["list of specific in-scope test items based on the architecture"],
  "scope_out_of_scope": ["list of out-of-scope items with reasons"],
  "scope_test_types": [
    {"type": "name", "description": "what it tests", "duration": "expected duration", "applicable": true}
  ],
  "environment_requirements": ["specific environment requirements based on the tech stack"],
  "environment_topology": [
    {"component": "name", "spec": "specification", "quantity": "number", "notes": "why"}
  ],
  "workload_model_users": {"normal": 0, "peak": 0, "stress": 0, "ramp_up": "duration", "steady_state": "duration"},
  "workload_model_transactions": [
    {"name": "transaction name", "type": "read/write", "weight_pct": 0, "think_time_s": "range"}
  ],
  "test_scenarios": [
    {"id": "TS-001", "name": "string", "objective": "string", "type": "string", "users": "string", "duration": "string", "pass_criteria": "string"}
  ],
  "test_data_requirements": [
    {"category": "string", "volume": "string", "source": "string", "method": "string"}
  ],
  "performance_targets_response_time": [
    {"transaction": "string", "p90": "string", "p95": "string", "p99": "string", "max": "string"}
  ],
  "performance_targets_resources": [
    {"metric": "string", "warning": "string", "critical": "string", "action": "string"}
  ],
  "performance_targets_availability": [
    {"metric": "string", "target": "string"}
  ],
  "risks": [
    {"risk": "string", "impact": "high/medium/low", "probability": "high/medium/low", "mitigation": "string"}
  ],
  "tools_testing": [
    {"tool": "string", "purpose": "string", "notes": "string"}
  ],
  "tools_monitoring": [
    {"layer": "string", "tool": "string", "metrics": "string"}
  ]
}

Make the content SPECIFIC to this project. Reference actual components, APIs, databases, and technologies from the HLD and NFR data. Do not use generic placeholder text."""


class AITestPlanWriter:
    def __init__(self, ai_client=None):
        self.ai = ai_client or AzureOpenAIClient()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(name="CoverTitle", parent=self.styles["Title"],
            fontSize=28, spaceAfter=12, textColor=colors.HexColor("#1a237e"), alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name="CoverSub", parent=self.styles["Normal"],
            fontSize=16, spaceAfter=6, textColor=colors.HexColor("#37474f"), alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name="SH", parent=self.styles["Heading1"],
            fontSize=16, spaceBefore=20, spaceAfter=10, textColor=colors.HexColor("#1a237e"),
            borderWidth=1, borderColor=colors.HexColor("#1a237e"), borderPadding=4))
        self.styles.add(ParagraphStyle(name="SS", parent=self.styles["Heading2"],
            fontSize=13, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#283593")))
        self.styles.add(ParagraphStyle(name="BT", parent=self.styles["Normal"],
            fontSize=10, spaceAfter=6, alignment=TA_JUSTIFY, leading=14))

    def generate(self, project_name, output_path, hld_analysis=None,
                 nfr_data=None, estimation_result=None, pet_ticket_id=None):

        context = self._build_context(project_name, hld_analysis, nfr_data, estimation_result)

        plan_content = self.ai.chat_json(
            system_prompt=TEST_PLAN_PROMPT,
            user_prompt=context,
            max_tokens=4000
        )

        return self._render_pdf(
            project_name, output_path, plan_content,
            estimation_result, pet_ticket_id, nfr_data
        )

    def _build_context(self, project_name, hld, nfr, estimation):
        parts = [f"Project: {project_name}"]
        if hld:
            parts.append(f"Architecture: {hld.get('architecture', {}).get('pattern', 'unknown')}")
            components = hld.get("architecture", {}).get("components", [])
            if components:
                parts.append(f"Components: {', '.join(c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in components)}")
            in_scope = hld.get("in_scope_items", [])
            if in_scope:
                parts.append(f"In-scope ({len(in_scope)}):")
                for item in in_scope[:15]:
                    parts.append(f"  - {item.get('name', item) if isinstance(item, dict) else item}")
            integrations = hld.get("integrations", [])
            if integrations:
                parts.append(f"Integrations: {', '.join(i.get('name', str(i)) if isinstance(i, dict) else str(i) for i in integrations)}")

        if nfr:
            wp = nfr.get("workload_profile", {})
            pt = nfr.get("performance_targets", {})
            parts.append(f"Users: {wp.get('concurrent_users_normal', 'TBD')} normal, {wp.get('concurrent_users_peak', 'TBD')} peak")
            parts.append(f"TPS: {wp.get('tps_peak', 'TBD')} peak")
            parts.append(f"Response time: {pt.get('response_time_read', 'TBD')}")
            parts.append(f"Availability: {pt.get('availability_sla', 'TBD')}")
            monitoring = nfr.get("monitoring_tools", [])
            if monitoring:
                parts.append(f"Monitoring: {', '.join(monitoring)}")
            tech = nfr.get("architecture", {}).get("tech_stack", {})
            if tech:
                parts.append(f"Tech stack: {tech}")

        if estimation:
            totals = estimation.get("totals", {})
            parts.append(f"Estimated effort: {totals.get('total_pd_after_efficiency', 'TBD')} PD")

        return "\n".join(parts)

    def _render_pdf(self, project_name, output_path, content,
                    estimation, pet_ticket_id, nfr_data):
        doc = SimpleDocTemplate(output_path, pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm, topMargin=25*mm, bottomMargin=20*mm)
        story = []

        # Cover
        story.append(Spacer(1, 80*mm))
        story.append(Paragraph("Performance Test Plan", self.styles["CoverTitle"]))
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph(project_name, self.styles["CoverSub"]))
        story.append(Paragraph("AI-Generated", self.styles["CoverSub"]))
        story.append(Spacer(1, 15*mm))
        ticket = pet_ticket_id or "PET-XXX"
        cover_data = [
            ["Document ID", f"PTP-{project_name.replace(' ', '-').upper()[:20]}"],
            ["PET Ticket", ticket], ["Version", "1.0"],
            ["Date", str(date.today())], ["Status", "Draft"],
            ["Generated By", "AI Estimation Agent (Azure OpenAI)"]
        ]
        ct = Table(cover_data, colWidths=[50*mm, 80*mm])
        ct.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#90a4ae")),
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#eceff1")),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("LEFTPADDING", (0,0), (-1,-1), 8), ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(ct)
        story.append(PageBreak())

        # Sections from AI content
        story.extend(self._section("1. Introduction", [
            ("1.1 Purpose", content.get("introduction_purpose", "")),
            ("1.2 Background", content.get("introduction_background", ""))
        ]))

        story.append(Paragraph("2. Scope", self.styles["SH"]))
        story.append(Paragraph("2.1 In-Scope", self.styles["SS"]))
        for item in content.get("scope_in_scope", []):
            story.append(Paragraph(f"• {item}", self.styles["BT"]))
        story.append(Paragraph("2.2 Out of Scope", self.styles["SS"]))
        for item in content.get("scope_out_of_scope", []):
            story.append(Paragraph(f"• {item}", self.styles["BT"]))
        test_types = content.get("scope_test_types", [])
        if test_types:
            story.append(Paragraph("2.3 Test Types", self.styles["SS"]))
            tt_data = [["Test Type", "Description", "Duration"]]
            for tt in test_types:
                if isinstance(tt, dict):
                    tt_data.append([tt.get("type",""), tt.get("description",""), tt.get("duration","")])
            story.append(self._table(tt_data, [35*mm, 80*mm, 45*mm]))

        # Environment
        story.append(Paragraph("3. Test Environment", self.styles["SH"]))
        env_reqs = content.get("environment_requirements", [])
        if env_reqs:
            for req in env_reqs:
                story.append(Paragraph(f"• {req}", self.styles["BT"]))
        env_topo = content.get("environment_topology", [])
        if env_topo:
            et_data = [["Component", "Specification", "Qty", "Notes"]]
            for e in env_topo:
                if isinstance(e, dict):
                    et_data.append([e.get("component",""), e.get("spec",""), str(e.get("quantity","")), e.get("notes","")])
            story.append(self._table(et_data, [35*mm, 45*mm, 20*mm, 60*mm]))

        # Workload
        story.append(Paragraph("4. Workload Model", self.styles["SH"]))
        wm = content.get("workload_model_users", {})
        if wm:
            wm_data = [["Parameter", "Normal", "Peak", "Stress"],
                ["Concurrent Users", str(wm.get("normal","")), str(wm.get("peak","")), str(wm.get("stress",""))],
                ["Ramp-up", wm.get("ramp_up",""), wm.get("ramp_up",""), "5 min"],
                ["Steady State", wm.get("steady_state",""), wm.get("steady_state",""), "Until failure"]]
            story.append(self._table(wm_data, [40*mm, 40*mm, 40*mm, 40*mm]))
        txns = content.get("workload_model_transactions", [])
        if txns:
            story.append(Paragraph("4.2 Transaction Mix", self.styles["SS"]))
            tx_data = [["Transaction", "Type", "Weight %", "Think Time"]]
            for t in txns:
                if isinstance(t, dict):
                    tx_data.append([t.get("name",""), t.get("type",""), str(t.get("weight_pct",""))+"%", str(t.get("think_time_s",""))+"s"])
            story.append(self._table(tx_data, [50*mm, 20*mm, 25*mm, 30*mm]))

        # Scenarios
        scenarios = content.get("test_scenarios", [])
        if scenarios:
            story.append(Paragraph("5. Test Scenarios", self.styles["SH"]))
            for s in scenarios:
                if isinstance(s, dict):
                    sd = [["Scenario ID", s.get("id","")], ["Name", s.get("name","")],
                          ["Objective", s.get("objective","")], ["Type", s.get("type","")],
                          ["Users", s.get("users","")], ["Duration", s.get("duration","")],
                          ["Pass Criteria", s.get("pass_criteria","")]]
                    st = Table(sd, colWidths=[35*mm, 125*mm])
                    st.setStyle(TableStyle([
                        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#bdbdbd")),
                        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8eaf6")),
                        ("FONTSIZE",(0,0),(-1,-1),9),
                        ("LEFTPADDING",(0,0),(-1,-1),6), ("TOPPADDING",(0,0),(-1,-1),4),
                        ("BOTTOMPADDING",(0,0),(-1,-1),4)]))
                    story.append(KeepTogether([st, Spacer(1,5*mm)]))

        # Performance targets
        rt = content.get("performance_targets_response_time", [])
        if rt:
            story.append(Paragraph("6. Performance Targets", self.styles["SH"]))
            story.append(Paragraph("6.1 Response Time", self.styles["SS"]))
            rt_data = [["Transaction", "p90", "p95", "p99", "Max"]]
            for r in rt:
                if isinstance(r, dict):
                    rt_data.append([r.get("transaction",""), r.get("p90",""), r.get("p95",""), r.get("p99",""), r.get("max","")])
            story.append(self._table(rt_data, [40*mm, 28*mm, 28*mm, 28*mm, 28*mm]))

        res = content.get("performance_targets_resources", [])
        if res:
            story.append(Paragraph("6.2 Resource Thresholds", self.styles["SS"]))
            res_data = [["Metric", "Warning", "Critical", "Action"]]
            for r in res:
                if isinstance(r, dict):
                    res_data.append([r.get("metric",""), r.get("warning",""), r.get("critical",""), r.get("action","")])
            story.append(self._table(res_data, [40*mm, 30*mm, 30*mm, 60*mm]))

        # Risks
        risks = content.get("risks", [])
        if risks:
            story.append(Paragraph("7. Risks & Mitigations", self.styles["SH"]))
            r_data = [["Risk", "Impact", "Prob.", "Mitigation"]]
            for r in risks:
                if isinstance(r, dict):
                    r_data.append([r.get("risk","")[:60], r.get("impact",""), r.get("probability",""), r.get("mitigation","")])
            story.append(self._table(r_data, [45*mm, 18*mm, 18*mm, 79*mm]))

        # Tools
        tools_t = content.get("tools_testing", [])
        tools_m = content.get("tools_monitoring", [])
        if tools_t or tools_m:
            story.append(Paragraph("8. Tools & Monitoring", self.styles["SH"]))
            if tools_t:
                tt_data = [["Tool", "Purpose", "Notes"]]
                for t in tools_t:
                    if isinstance(t, dict):
                        tt_data.append([t.get("tool",""), t.get("purpose",""), t.get("notes","")])
                story.append(self._table(tt_data, [45*mm, 55*mm, 60*mm]))
            if tools_m:
                story.append(Paragraph("8.2 Monitoring", self.styles["SS"]))
                mm_data = [["Layer", "Tool", "Metrics"]]
                for m in tools_m:
                    if isinstance(m, dict):
                        mm_data.append([m.get("layer",""), m.get("tool",""), m.get("metrics","")])
                story.append(self._table(mm_data, [30*mm, 60*mm, 70*mm]))

        doc.build(story)
        return output_path

    def _section(self, title, subsections):
        elements = [Paragraph(title, self.styles["SH"])]
        for subtitle, content in subsections:
            elements.append(Paragraph(subtitle, self.styles["SS"]))
            elements.append(Paragraph(content, self.styles["BT"]))
        return elements

    def _table(self, data, widths):
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1a237e")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTSIZE",(0,0),(-1,0),9), ("FONTSIZE",(0,1),(-1,-1),8),
            ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#bdbdbd")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6),
            ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4)]))
        return t
