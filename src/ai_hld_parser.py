"""
AI-powered HLD document parser.
Uses Azure OpenAI to intelligently extract project scope, architecture,
and NFR-relevant information from High-Level Design documents.
"""

from .azure_openai_client import AzureOpenAIClient


HLD_PARSING_PROMPT = """You are a senior performance engineer analyzing a High-Level Design (HLD) document to prepare a performance estimation.

Extract ALL performance-relevant information and return as JSON:

{
  "project_name": "string",
  "project_description": "string",
  "business_objectives": ["list of objectives"],
  "in_scope_items": [
    {
      "id": "string (e.g., IS-01)",
      "name": "string",
      "type": "api | batch | ui | integration | event",
      "description": "string"
    }
  ],
  "out_of_scope_items": ["items explicitly excluded"],
  "use_cases": [
    {
      "id": "string (e.g., UC-01)",
      "name": "string",
      "description": "string",
      "complexity": "simple | medium | complex"
    }
  ],
  "data_entities": [
    {
      "name": "string",
      "estimated_volume": "string or null",
      "growth_rate": "string or null"
    }
  ],
  "architecture": {
    "pattern": "monolith | microservices | serverless | hybrid",
    "components": [
      {
        "name": "string",
        "type": "service | database | queue | cache | gateway",
        "technology": "string"
      }
    ],
    "communication_patterns": ["sync REST | async messaging | gRPC | GraphQL"],
    "deployment": "kubernetes | ecs | vm | serverless | on-prem"
  },
  "integrations": [
    {
      "name": "string",
      "type": "inbound | outbound",
      "protocol": "REST | SOAP | messaging | file",
      "sla_dependency": true
    }
  ],
  "security_requirements": {
    "authentication": "string",
    "authorization": "string",
    "encryption": "string",
    "compliance": ["list of compliance requirements"]
  },
  "nfr_mentioned": {
    "response_time": "string or null",
    "availability": "string or null",
    "throughput": "string or null",
    "scalability": "string or null",
    "data_retention": "string or null"
  },
  "performance_risk_factors": [
    {
      "factor": "string",
      "risk_level": "high | medium | low",
      "reasoning": "why this impacts performance"
    }
  ],
  "project_size_indicators": {
    "in_scope_count": "number",
    "use_case_count": "number",
    "data_entity_count": "number",
    "integration_count": "number",
    "recommended_size": "small | medium | large",
    "sizing_reasoning": "explain why this size classification"
  }
}

Be thorough in identifying in-scope items. Count APIs, batch jobs, UI flows, and integrations separately. Flag any performance risk factors you identify from the architecture (e.g., synchronous calls in microservices, large batch volumes, complex join queries, missing caching layers)."""


class AIHLDParser:
    def __init__(self, ai_client=None):
        self.ai = ai_client or AzureOpenAIClient()

    def parse(self, hld_content):
        result = self.ai.chat_json(
            system_prompt=HLD_PARSING_PROMPT,
            user_prompt=f"HLD Document:\n\n{hld_content}",
            max_tokens=4000
        )
        return result

    def parse_file(self, file_path):
        if file_path.endswith(".docx"):
            content = self._read_docx(file_path)
        elif file_path.endswith(".pdf"):
            content = self._read_pdf(file_path)
        else:
            with open(file_path) as f:
                content = f.read()
        return self.parse(content)

    def classify_size(self, parsed_hld):
        indicators = parsed_hld.get("project_size_indicators", {})
        in_scope = indicators.get("in_scope_count", 0)
        use_cases = indicators.get("use_case_count", 0)
        data_entities = indicators.get("data_entity_count", 0)

        if in_scope <= 5 and use_cases <= 5 and data_entities <= 3:
            return "small"
        elif in_scope <= 15 and use_cases <= 15:
            return "medium"
        else:
            return "large"

    def suggest_estimation_adjustments(self, parsed_hld):
        risk_factors = parsed_hld.get("performance_risk_factors", [])
        architecture = parsed_hld.get("architecture", {})
        integrations = parsed_hld.get("integrations", [])

        prompt = f"""Based on this HLD analysis, suggest specific adjustments to the PERF estimation:

Architecture: {architecture.get('pattern', 'unknown')}
Components: {len(architecture.get('components', []))}
Integrations: {len(integrations)} ({sum(1 for i in integrations if i.get('sla_dependency')))} with SLA dependency)
Risk Factors: {len(risk_factors)}

Risk details:
{chr(10).join(f"- {r['factor']} ({r['risk_level']}): {r['reasoning']}" for r in risk_factors)}

For each of the 11 PERF activities (Analysis, Assessment, Batch Job Execution, Data Prep, Defects Management, Execution - Peak Load, Execution - Stress Test, HP PC Support, Planning, Reporting, Script Design), suggest unit adjustments (+1, +2, -1, or 0) with reasoning.

Return as JSON:
{{
  "adjustments": [
    {{
      "activity": "Activity Name",
      "unit_change": 0,
      "reasoning": "why"
    }}
  ],
  "overall_complexity_note": "summary of what makes this project more/less complex than average"
}}"""

        return self.ai.chat_json(
            system_prompt="You are a performance estimation expert calibrating PERF activity units based on project architecture and risk factors.",
            user_prompt=prompt
        )

    def _read_docx(self, file_path):
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            with open(file_path, "rb") as f:
                return f.read().decode("utf-8", errors="ignore")

    def _read_pdf(self, file_path):
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return "[PDF reading requires PyPDF2 - install with: pip install PyPDF2]"
