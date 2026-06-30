# AI-Powered Autonomous Estimation Agent

An autonomous performance estimation agent powered by Azure OpenAI. Unlike the rule-based estimation agent, this version uses AI for every step - parsing HLDs, analyzing transcripts, reasoning about estimation adjustments, and writing test plan content.

## Architecture

```
Outlook Email (PET notification)
    |
    v
Email Trigger (Graph API)
    |
    v
Autonomous Agent
    |
    +-> AI HLD Parser (Azure OpenAI)
    |     -> Extracts scope, architecture, risk factors
    |     -> Classifies project size with reasoning
    |
    +-> AI Estimation Engine (Azure OpenAI)
    |     -> Calculates PERF activities with intelligent adjustments
    |     -> Provides risk-based reasoning for unit changes
    |
    +-> Meeting Scheduler
    |     -> Drafts .ics file for NFR discovery meeting
    |
    +-> AI Transcript Analyzer (Azure OpenAI)
    |     -> Extracts NFR data with context understanding
    |     -> Identifies implicit requirements
    |     -> Scores meeting coverage, flags gaps
    |     -> Generates follow-up questions
    |
    +-> AI Test Plan Writer (Azure OpenAI)
    |     -> Generates project-specific test plan content
    |     -> Renders professional PDF
    |
    +-> Jira MCP (posts results)
```

## What Makes This Different from the Rule-Based Agent

| Feature | Rule-Based Agent | AI Agent |
|---------|-----------------|----------|
| HLD Parsing | Manual/regex extraction | AI understands document structure and context |
| Transcript Analysis | Regex pattern matching | AI understands conversation, implied requirements |
| Estimation | Fixed rules + size lookup | AI reasons about risk factors and adjusts with explanations |
| Test Plan Content | Template-based fill-in | AI writes project-specific content for each section |
| Follow-up | Manual | AI identifies gaps and generates follow-up questions |
| Meeting Coverage | Not assessed | AI scores NFR coverage quality |

## Quick Start

### 1. Set Environment Variables

```bash
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_API_KEY=your-api-key
export AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### 2. Install Dependencies

```bash
pip install openai pyyaml reportlab requests python-docx PyPDF2
```

### 3. Run the Demo

```bash
python3 -m examples.demo_ai_agent
```

Without Azure OpenAI credentials, it runs in dry-run mode showing what each step does.

### 4. Use Programmatically

```python
from src.autonomous_agent import AutonomousEstimationAgent

agent = AutonomousEstimationAgent()

# Phase 1: Process PET ticket + HLD
result = agent.process_pet_ticket(
    pet_ticket_id="PET-001",
    perf_manager_email="you@company.com",
    hld_content=open("path/to/hld.md").read(),
    output_dir="output"
)

# Phase 2: Process meeting transcript
transcript_result = agent.process_transcript(
    pet_ticket_id="PET-001",
    transcript_content=open("meeting.vtt").read(),
    transcript_format="vtt",
    output_dir="output"
)

print(f"Test Plan: {transcript_result['test_plan_pdf']}")
print(f"Follow-ups: {transcript_result['follow_up_count']}")
```

## AI Components

### AI HLD Parser
Sends the HLD document to Azure OpenAI and extracts:
- In-scope items with types (API, batch, UI, integration)
- Use cases with complexity classification
- Architecture pattern and components
- External integrations with SLA dependencies
- Performance risk factors with severity and reasoning
- Project size classification with explanation

### AI Transcript Analyzer
Sends the Teams meeting transcript to Azure OpenAI and extracts:
- Structured NFR data (workload, targets, SLAs)
- Architecture details discussed during HLD walkthrough
- Known issues with severity assessment
- Open items with owners
- Risks with impact assessment
- Implicit requirements (things implied but not explicitly stated)
- Meeting quality score (coverage percentage, gaps, follow-up needed)

### AI Estimation Engine
Sends project analysis to Azure OpenAI and produces:
- Project size classification with reasoning
- PERF activity units with intelligent adjustments
- Risk-based adjustment explanations
- AI insights about project complexity
- Calibration mode (adjust based on feedback)

### AI Test Plan Writer
Sends all project data to Azure OpenAI and generates:
- Project-specific test plan content (not templates)
- Test scenarios tailored to actual architecture
- Transaction mix based on real workload profile
- Environment topology matching identified tech stack
- Risks specific to this project's characteristics

## Project Structure

```
estimation-agent-ai/
  src/
    azure_openai_client.py        # Azure OpenAI SDK wrapper
    ai_hld_parser.py              # AI-powered HLD analysis
    ai_transcript_analyzer.py     # AI-powered transcript NFR extraction
    ai_estimation_engine.py       # AI-powered PERF estimation
    ai_test_plan_writer.py        # AI-generated test plan PDF
    autonomous_agent.py           # Full pipeline orchestrator
    email_trigger.py              # Outlook email monitoring
    meeting_scheduler.py          # Teams meeting .ics generation
  config/
    estimation_rules.yaml         # PERF activity base times
    nfr_questionnaire.yaml        # 34 NFR discovery questions
  examples/
    demo_ai_agent.py              # Full workflow demo
  .github/agents/
    (use with Copilot/Claude Code for interactive mode)
```

## Azure OpenAI Setup

1. Create an Azure OpenAI resource in Azure Portal
2. Deploy a GPT-4o model (or GPT-4 Turbo)
3. Copy the endpoint URL and API key
4. Set the deployment name in AZURE_OPENAI_DEPLOYMENT

Required Azure OpenAI permissions: Cognitive Services OpenAI User

For email trigger (optional):
- Register an Azure AD app with Mail.Read permission
- Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID, AZURE_REFRESH_TOKEN

## Output Files

Per PET ticket, the agent generates:
- hld_analysis_PET-XXX.json - Structured HLD analysis
- estimation_PET-XXX.json - PERF estimation with AI reasoning
- estimation_report_PET-XXX.txt - Formatted estimation report
- adjustments_PET-XXX.json - AI-suggested risk adjustments
- meeting_draft_PET-XXX.json - Meeting event data
- NFR_Discovery_PET-XXX.ics - Calendar invite file
- meeting_invite_PET-XXX.html - Meeting body HTML
- nfr_analysis_PET-XXX.json - AI transcript analysis
- estimation_updated_PET-XXX.txt - Updated estimation after meeting
- follow_up_PET-XXX.json - AI-generated follow-up questions
- Performance_Test_Plan_PET-XXX.pdf - AI-written test plan
- agent_state_PET-XXX.json - Pipeline state for continuity
