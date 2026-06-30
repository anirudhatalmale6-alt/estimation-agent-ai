"""
AI-powered Teams meeting transcript analyzer.
Uses Azure OpenAI to intelligently extract NFR data from meeting transcripts,
going beyond regex to understand context, intent, and implicit requirements.
"""

import re
from .azure_openai_client import AzureOpenAIClient


TRANSCRIPT_ANALYSIS_PROMPT = """You are a senior performance engineer analyzing a Microsoft Teams meeting transcript from an NFR (Non-Functional Requirements) discovery session.

Your task is to extract ALL performance-relevant information from the conversation and return a structured JSON response.

Extract the following and return as JSON:

{
  "project_overview": {
    "project_name": "string",
    "description": "string",
    "go_live_date": "string or null",
    "change_type": "new_application | major_release | minor_release | patch",
    "available_environments": ["list of environments mentioned"]
  },
  "architecture": {
    "components": ["list of system components"],
    "tech_stack": {
      "languages": ["programming languages"],
      "databases": ["databases"],
      "middleware": ["message queues, ESBs"],
      "cloud_platform": "string or null",
      "containerization": "string or null"
    },
    "external_integrations": ["third-party services"],
    "authentication": "description of auth mechanism"
  },
  "workload_profile": {
    "concurrent_users_normal": "number or null",
    "concurrent_users_peak": "number or null",
    "peak_timing": "when peak occurs",
    "tps_normal": "number or null",
    "tps_peak": "number or null",
    "critical_transactions": ["list of critical business transactions"],
    "batch_jobs": [
      {
        "name": "string",
        "frequency": "string",
        "volume": "string",
        "sla": "string"
      }
    ],
    "data_growth_rate": "string or null"
  },
  "performance_targets": {
    "response_time_read": "string (e.g., '< 2 seconds')",
    "response_time_write": "string",
    "availability_sla": "string (e.g., '99.95%')",
    "error_rate_threshold": "string (e.g., '< 0.5%')",
    "cpu_threshold": "string (e.g., '< 65%')",
    "memory_threshold": "string (e.g., '< 75%')",
    "throughput_target": "string or null",
    "batch_sla": "string or null"
  },
  "data_requirements": {
    "test_data_approach": "masked_production | synthetic | mixed | unknown",
    "data_volume_description": "string",
    "data_retention_policy": "string or null"
  },
  "monitoring_tools": ["list of APM, logging, infra monitoring tools"],
  "known_issues": [
    {
      "description": "string",
      "mentioned_by": "speaker name",
      "severity": "high | medium | low"
    }
  ],
  "open_items": [
    {
      "description": "string",
      "owner": "who needs to follow up",
      "mentioned_by": "speaker name"
    }
  ],
  "risks": [
    {
      "description": "string",
      "impact": "high | medium | low",
      "mentioned_by": "speaker name"
    }
  ],
  "key_contacts": [
    {
      "name": "string",
      "role": "string"
    }
  ],
  "implicit_requirements": [
    "requirements not explicitly stated but implied by the discussion"
  ],
  "meeting_quality_score": {
    "coverage": "percentage of standard NFR areas covered",
    "gaps": ["NFR areas NOT discussed that should have been"],
    "follow_up_needed": true
  }
}

Be thorough. Extract numeric values with their units. Identify implicit requirements from context (e.g., if they mention Kubernetes, imply container scaling behavior needs testing). Flag areas that were NOT discussed but should have been for a complete NFR assessment."""


class AITranscriptAnalyzer:
    def __init__(self, ai_client=None):
        self.ai = ai_client or AzureOpenAIClient()

    def parse_vtt(self, vtt_content):
        entries = []
        blocks = re.split(r"\n\n+", vtt_content.strip())
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 2:
                continue
            timestamp_line = None
            speaker = None
            text_lines = []
            for line in lines:
                if "-->" in line:
                    timestamp_line = line.strip()
                elif line.startswith("<v "):
                    match = re.match(r"<v ([^>]+)>(.*)", line)
                    if match:
                        speaker = match.group(1).strip()
                        text_lines.append(match.group(2).strip())
                elif timestamp_line:
                    text_lines.append(line.strip())
            if timestamp_line and text_lines:
                start_time = timestamp_line.split("-->")[0].strip()
                entries.append({
                    "timestamp": start_time,
                    "speaker": speaker or "Unknown",
                    "text": " ".join(text_lines)
                })
        return entries

    def analyze(self, transcript_content, format="vtt"):
        if format == "vtt":
            entries = self.parse_vtt(transcript_content)
        else:
            entries = self._parse_plain_text(transcript_content)

        conversation_text = "\n".join(
            f"[{e['timestamp']}] {e['speaker']}: {e['text']}" for e in entries
        )

        speakers = list(set(e["speaker"] for e in entries))

        result = self.ai.chat_json(
            system_prompt=TRANSCRIPT_ANALYSIS_PROMPT,
            user_prompt=f"Meeting transcript ({len(entries)} entries, {len(speakers)} speakers: {', '.join(speakers)}):\n\n{conversation_text}",
            max_tokens=4000
        )

        result["_meta"] = {
            "entry_count": len(entries),
            "speakers": speakers,
            "duration_estimate": entries[-1]["timestamp"] if entries else "unknown"
        }

        return result

    def generate_follow_up_questions(self, analysis_result):
        gaps = analysis_result.get("meeting_quality_score", {}).get("gaps", [])
        open_items = analysis_result.get("open_items", [])

        prompt = f"""Based on this NFR discovery analysis, generate follow-up questions for the next meeting or email to the project team.

Gaps identified (areas not discussed):
{chr(10).join(f'- {g}' for g in gaps)}

Open items:
{chr(10).join(f'- {item["description"]} (owner: {item.get("owner", "TBD")})' for item in open_items)}

Generate a numbered list of specific, actionable follow-up questions. Focus on what's missing for a complete performance test plan. Return as JSON:
{{"follow_up_questions": ["question 1", "question 2", ...]}}"""

        return self.ai.chat_json(
            system_prompt="You are a performance engineering lead preparing follow-up questions after an NFR discovery session.",
            user_prompt=prompt
        )

    def _parse_plain_text(self, text):
        entries = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            entries.append({
                "timestamp": "",
                "speaker": "Unknown",
                "text": line
            })
        return entries
