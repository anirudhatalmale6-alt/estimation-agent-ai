"""
Autonomous estimation agent.
Ties together all AI-powered components into a single autonomous pipeline
triggered by email notifications.

Flow:
1. Email trigger detects PET ticket notification
2. AI reads and parses HLD document from Jira
3. AI analyzes project complexity and generates estimation
4. AI posts estimation to Jira and drafts NFR meeting
5. After meeting: AI analyzes transcript and generates test plan PDF
"""

import os
import json
from datetime import date

from .azure_openai_client import AzureOpenAIClient
from .ai_transcript_analyzer import AITranscriptAnalyzer
from .ai_hld_parser import AIHLDParser
from .ai_estimation_engine import AIEstimationEngine
from .ai_test_plan_writer import AITestPlanWriter


class AutonomousEstimationAgent:
    def __init__(self, azure_openai_client=None, jira_client=None):
        self.ai = azure_openai_client or AzureOpenAIClient()
        self.jira = jira_client

        self.hld_parser = AIHLDParser(self.ai)
        self.transcript_analyzer = AITranscriptAnalyzer(self.ai)
        self.estimation_engine = AIEstimationEngine(self.ai)
        self.test_plan_writer = AITestPlanWriter(self.ai)

    def process_pet_ticket(self, pet_ticket_id, perf_manager_email,
                           hld_content=None, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        log = []

        # Step 1: Read PET ticket
        self._log(log, "read_ticket", f"Reading PET ticket {pet_ticket_id}")
        ticket_data = None
        if self.jira:
            ticket_data = self.jira.get_issue(pet_ticket_id)
        else:
            ticket_data = {
                "key": pet_ticket_id,
                "fields": {
                    "summary": f"Performance Estimation - {pet_ticket_id}",
                    "reporter": {"displayName": "Project Manager", "emailAddress": "pm@company.com"}
                }
            }

        # Step 2: Parse HLD with AI
        self._log(log, "parse_hld", "AI parsing HLD document")
        if hld_content:
            hld_analysis = self.hld_parser.parse(hld_content)
        else:
            hld_analysis = self._default_hld_analysis(pet_ticket_id)

        hld_path = os.path.join(output_dir, f"hld_analysis_{pet_ticket_id}.json")
        with open(hld_path, "w") as f:
            json.dump(hld_analysis, f, indent=2, default=str)

        # Step 3: AI estimation with intelligent adjustments
        self._log(log, "estimate", "AI calculating PERF estimation with risk-based adjustments")
        estimation = self.estimation_engine.estimate(
            hld_analysis=hld_analysis,
            pet_ticket_id=pet_ticket_id
        )

        report_text = self.estimation_engine.format_report(estimation)
        report_path = os.path.join(output_dir, f"estimation_report_{pet_ticket_id}.txt")
        with open(report_path, "w") as f:
            f.write(report_text)

        estimation_path = os.path.join(output_dir, f"estimation_{pet_ticket_id}.json")
        with open(estimation_path, "w") as f:
            json.dump(estimation, f, indent=2, default=str)

        # Step 4: Post to Jira
        self._log(log, "post_jira", f"Posting estimation to {pet_ticket_id}")
        if self.jira:
            self.jira.add_comment(pet_ticket_id, report_text)

        # Step 5: Draft meeting invite
        self._log(log, "draft_meeting", "Drafting NFR discovery meeting")
        from .meeting_scheduler import MeetingScheduler
        scheduler = MeetingScheduler()
        pm_name = ticket_data.get("fields", {}).get("reporter", {}).get("displayName", "PM")
        pm_email = ticket_data.get("fields", {}).get("reporter", {}).get("emailAddress", "pm@company.com")
        project_name = hld_analysis.get("project_name", pet_ticket_id)

        meeting_files = scheduler.draft_and_save(
            project_name=project_name,
            pet_ticket_id=pet_ticket_id,
            pm_name=pm_name,
            pm_email=pm_email,
            perf_manager_email=perf_manager_email,
            estimation_summary=report_text,
            output_dir=output_dir
        )

        # Step 6: Suggest estimation adjustments based on HLD risks
        self._log(log, "suggest_adjustments", "AI analyzing risk-based adjustments")
        adjustments = self.hld_parser.suggest_estimation_adjustments(hld_analysis)
        adj_path = os.path.join(output_dir, f"adjustments_{pet_ticket_id}.json")
        with open(adj_path, "w") as f:
            json.dump(adjustments, f, indent=2, default=str)

        result = {
            "pet_ticket_id": pet_ticket_id,
            "project_name": project_name,
            "pm_name": pm_name,
            "pm_email": pm_email,
            "estimation": estimation.get("totals", {}),
            "hld_analysis_path": hld_path,
            "estimation_report_path": report_path,
            "meeting_files": meeting_files,
            "adjustments_path": adj_path,
            "log": log,
            "status": "awaiting_nfr_meeting"
        }

        state_path = os.path.join(output_dir, f"agent_state_{pet_ticket_id}.json")
        with open(state_path, "w") as f:
            json.dump(result, f, indent=2, default=str)

        return result

    def process_transcript(self, pet_ticket_id, transcript_content,
                           transcript_format="vtt", output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        log = []

        # Load previous state
        state_path = os.path.join(output_dir, f"agent_state_{pet_ticket_id}.json")
        prev_state = {}
        if os.path.exists(state_path):
            with open(state_path) as f:
                prev_state = json.load(f)

        # Load HLD analysis
        hld_analysis = None
        hld_path = os.path.join(output_dir, f"hld_analysis_{pet_ticket_id}.json")
        if os.path.exists(hld_path):
            with open(hld_path) as f:
                hld_analysis = json.load(f)

        # Load estimation
        estimation = None
        est_path = os.path.join(output_dir, f"estimation_{pet_ticket_id}.json")
        if os.path.exists(est_path):
            with open(est_path) as f:
                estimation = json.load(f)

        # Step 6: AI transcript analysis
        self._log(log, "analyze_transcript", "AI analyzing meeting transcript")
        nfr_data = self.transcript_analyzer.analyze(transcript_content, format=transcript_format)

        nfr_path = os.path.join(output_dir, f"nfr_analysis_{pet_ticket_id}.json")
        with open(nfr_path, "w") as f:
            json.dump(nfr_data, f, indent=2, default=str)

        # Step 7: Re-estimate with NFR data
        self._log(log, "re_estimate", "AI re-estimating with NFR data from meeting")
        updated_estimation = self.estimation_engine.estimate(
            hld_analysis=hld_analysis,
            nfr_data=nfr_data,
            pet_ticket_id=pet_ticket_id
        )

        updated_report = self.estimation_engine.format_report(updated_estimation)
        updated_path = os.path.join(output_dir, f"estimation_updated_{pet_ticket_id}.txt")
        with open(updated_path, "w") as f:
            f.write(updated_report)

        # Step 8: Generate follow-up questions
        self._log(log, "follow_up", "AI generating follow-up questions for gaps")
        follow_ups = self.transcript_analyzer.generate_follow_up_questions(nfr_data)
        fu_path = os.path.join(output_dir, f"follow_up_{pet_ticket_id}.json")
        with open(fu_path, "w") as f:
            json.dump(follow_ups, f, indent=2, default=str)

        # Step 9: AI-generated test plan PDF
        self._log(log, "generate_test_plan", "AI writing Performance Test Plan PDF")
        project_name = prev_state.get("project_name", pet_ticket_id)
        pdf_path = os.path.join(output_dir, f"Performance_Test_Plan_{pet_ticket_id}.pdf")

        self.test_plan_writer.generate(
            project_name=project_name,
            output_path=pdf_path,
            hld_analysis=hld_analysis,
            nfr_data=nfr_data,
            estimation_result=updated_estimation,
            pet_ticket_id=pet_ticket_id
        )

        # Step 10: Post to Jira
        if self.jira:
            self.jira.add_comment(
                pet_ticket_id,
                f"AI-Generated Performance Test Plan ready.\n\n"
                f"Updated estimation after NFR meeting:\n{updated_report}\n\n"
                f"Follow-up items: {len(follow_ups.get('follow_up_questions', []))}"
            )

        return {
            "pet_ticket_id": pet_ticket_id,
            "nfr_analysis_path": nfr_path,
            "updated_estimation_path": updated_path,
            "follow_up_path": fu_path,
            "test_plan_pdf": pdf_path,
            "updated_estimation": updated_estimation.get("totals", {}),
            "transcript_meta": nfr_data.get("_meta", {}),
            "follow_up_count": len(follow_ups.get("follow_up_questions", [])),
            "log": log,
            "status": "test_plan_generated"
        }

    def _default_hld_analysis(self, pet_ticket_id):
        return {
            "project_name": pet_ticket_id,
            "project_description": "Details to be extracted from HLD attachment",
            "in_scope_items": [],
            "use_cases": [],
            "data_entities": [],
            "architecture": {"pattern": "unknown", "components": []},
            "integrations": [],
            "performance_risk_factors": [],
            "project_size_indicators": {
                "in_scope_count": 0, "use_case_count": 0,
                "data_entity_count": 0, "recommended_size": "medium"
            }
        }

    def _log(self, log_list, step, message):
        print(f"  [{step}] {message}")
        log_list.append({"step": step, "message": message, "date": str(date.today())})
