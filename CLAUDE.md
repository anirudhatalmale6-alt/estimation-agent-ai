# AI-Powered Autonomous Estimation Agent

Uses Azure OpenAI (GPT-4o) for intelligent HLD parsing, transcript analysis, estimation reasoning, and test plan content generation.

## Components
- src/azure_openai_client.py - Azure OpenAI SDK wrapper
- src/ai_hld_parser.py - AI-powered HLD document analysis
- src/ai_transcript_analyzer.py - AI-powered Teams transcript NFR extraction
- src/ai_estimation_engine.py - AI-powered PERF estimation with risk-based adjustments
- src/ai_test_plan_writer.py - AI-generated test plan PDF content
- src/autonomous_agent.py - Full pipeline orchestrator
- src/email_trigger.py - Outlook email monitoring via Graph API
- src/meeting_scheduler.py - Teams meeting .ics generation

## Configuration
- .env: Azure OpenAI endpoint, API key, deployment name
- config/estimation_rules.yaml: PERF activity base times and multipliers
- config/nfr_questionnaire.yaml: 34 standard NFR questions
