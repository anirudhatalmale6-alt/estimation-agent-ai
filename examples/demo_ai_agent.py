"""
Demo: AI-Powered Autonomous Estimation Agent.

Shows the full pipeline using Azure OpenAI for intelligent analysis.
Set environment variables before running:
    export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
    export AZURE_OPENAI_API_KEY=your-key
    export AZURE_OPENAI_DEPLOYMENT=gpt-4o

Usage:
    python3 -m examples.demo_ai_agent
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SAMPLE_HLD = """
# Billing Gateway v2.1 - High Level Design

## 1. Project Overview
The Billing Gateway is a middleware service that handles customer billing operations for the telecom platform. It processes payments, generates invoices, and manages billing cycles for 2M+ customer accounts.

## 2. Business Objectives
- Reduce billing cycle processing time by 30%
- Support real-time payment processing via Stripe
- Enable event-driven architecture for downstream CRM integration
- Achieve 99.95% availability SLA

## 3. In-Scope
- IS-01: Account Lookup API (GET /api/accounts/{id})
- IS-02: Payment Processing API (POST /api/payments)
- IS-03: Billing Cycle Trigger API (POST /api/billing/cycle)
- IS-04: Invoice Generation Service
- IS-05: Nightly Batch Billing Cycle (500K accounts)
- IS-06: Kafka Event Publisher (billing events to CRM)
- IS-07: Payment Reconciliation Batch Job
- IS-08: Account Balance Calculator
- IS-09: Rate Plan Engine
- IS-10: Usage Aggregation Service

## 4. Out of Scope
- Customer-facing UI (handled by frontend team)
- CRM downstream processing
- Legacy billing system decommission

## 5. Use Cases
- UC-01: Customer looks up account balance
- UC-02: Customer makes a one-time payment
- UC-03: System processes recurring auto-pay
- UC-04: Nightly billing cycle runs for all active accounts
- UC-05: System generates monthly invoices
- UC-06: Payment gateway processes refund
- UC-07: Rate plan change mid-cycle proration
- UC-08: Usage data aggregation from network elements
- UC-09: Revenue reconciliation report generation
- UC-10: Delinquent account flagging

## 6. Architecture
- Pattern: Microservices
- Language: Java 17, Spring Boot 3.2
- Database: Oracle 19c (accounts, billing), Redis (caching)
- Messaging: Apache Kafka (event streaming)
- Container: Kubernetes (EKS)
- API Gateway: Kong
- Authentication: OAuth 2.0 / JWT
- CI/CD: Jenkins + ArgoCD

## 7. External Integrations
- Stripe Payment Gateway (outbound, SLA-dependent)
- SendGrid Email Service (outbound)
- Kafka -> CRM System (async events)
- Network Usage Data Feed (inbound, file-based)

## 8. Data Entities
- Customer Account
- Payment Transaction
- Invoice
- Billing Cycle
- Rate Plan
- Usage Record
- Payment Method

## 9. Non-Functional Requirements
- Response time: < 2 seconds for API calls
- Availability: 99.95%
- Batch processing: 500K accounts in < 4 hours
- Error rate: < 0.5%
- CPU: < 65%, Memory: < 75%
"""

SAMPLE_TRANSCRIPT = """WEBVTT

00:00:01.000 --> 00:00:08.000
<v Sarah Johnson>Welcome to the NFR discovery for Billing Gateway v2.1. Mike, let's start with the architecture walkthrough.

00:00:09.000 --> 00:00:25.000
<v Mike Chen>Sure. We have a Java Spring Boot microservices architecture on Kubernetes. Oracle 19c for the main billing database, Redis for caching, and Kafka for event streaming to the CRM team.

00:00:26.000 --> 00:00:40.000
<v Mike Chen>Three main APIs - account lookup, payment processing, and billing cycle trigger. The billing cycle is a nightly batch job processing 500000 customer accounts.

00:00:41.000 --> 00:00:55.000
<v Sarah Johnson>What are the load expectations?

00:00:56.000 --> 00:01:10.000
<v Mike Chen>Normal hours about 2000 concurrent users, peak is 5000 on the first of the month. We target 500 transactions per second at peak.

00:01:11.000 --> 00:01:25.000
<v Mike Chen>API response time should be under 2 seconds for reads, 3 seconds for payment writes. We need 99.95 percent availability.

00:01:26.000 --> 00:01:35.000
<v Mike Chen>Error rate below 0.5 percent. CPU under 65 percent, memory under 75 percent.

00:01:36.000 --> 00:01:50.000
<v Lisa Park>Last release we had a known issue where the billing cycle query caused CPU to spike to 95 percent. We've added database indexes but need to validate under load.

00:01:51.000 --> 00:02:05.000
<v Mike Chen>The batch billing cycle must complete within 4 hours. We also have a payment reconciliation batch that runs at 6 AM.

00:02:06.000 --> 00:02:20.000
<v Mike Chen>We integrate with Stripe for payments and SendGrid for emails. Both are SLA-dependent - if Stripe is slow, our payment API is slow.

00:02:21.000 --> 00:02:30.000
<v Sarah Johnson>What about test data?

00:02:31.000 --> 00:02:40.000
<v Lisa Park>We need to check with security about using masked production data. Might need synthetic generation for payment records.

00:02:41.000 --> 00:02:55.000
<v Mike Chen>Monitoring-wise we have Dynatrace for APM, Grafana plus Prometheus for infrastructure, and Splunk for logs. Pre-Prod environment mirrors production.

00:02:56.000 --> 00:03:05.000
<v Mike Chen>Go-live is August 15th. Code freeze is August 1st.
"""


def main():
    print("=" * 70)
    print("  AI-POWERED AUTONOMOUS ESTIMATION AGENT DEMO")
    print("=" * 70)

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    if not endpoint or not api_key:
        print("\n  Azure OpenAI credentials not set.")
        print("  Set these environment variables to run with real AI:")
        print("    export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
        print("    export AZURE_OPENAI_API_KEY=your-key")
        print("    export AZURE_OPENAI_DEPLOYMENT=gpt-4o")
        print("\n  Running in DRY RUN mode (showing what the agent would do)...")
        dry_run(SAMPLE_HLD, SAMPLE_TRANSCRIPT)
        return

    from src.autonomous_agent import AutonomousEstimationAgent

    output_dir = "examples/output"
    os.makedirs(output_dir, exist_ok=True)

    agent = AutonomousEstimationAgent()

    print("\n--- PHASE 1: PET Ticket + HLD Processing ---")
    result = agent.process_pet_ticket(
        pet_ticket_id="PET-2847",
        perf_manager_email="sarah.johnson@company.com",
        hld_content=SAMPLE_HLD,
        output_dir=output_dir
    )

    print(f"\n  Estimation: {result['estimation']}")
    print(f"  Meeting drafted for: {result['pm_name']}")

    print("\n--- PHASE 2: Transcript Processing ---")
    transcript_result = agent.process_transcript(
        pet_ticket_id="PET-2847",
        transcript_content=SAMPLE_TRANSCRIPT,
        transcript_format="vtt",
        output_dir=output_dir
    )

    print(f"\n  Test Plan PDF: {transcript_result['test_plan_pdf']}")
    print(f"  Updated estimation: {transcript_result['updated_estimation']}")
    print(f"  Follow-up questions: {transcript_result['follow_up_count']}")

    print("\n--- Output Files ---")
    for f in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, f)
        if os.path.isfile(fpath):
            print(f"  {f} ({os.path.getsize(fpath):,} bytes)")

    print("\n" + "=" * 70)
    print("  Done.")
    print("=" * 70)


def dry_run(hld, transcript):
    print("\n  PHASE 1 - What the agent would do:")
    print("  1. Send HLD to Azure OpenAI for AI-powered parsing")
    print("     -> Extract in-scope items, use cases, architecture, risk factors")
    print("     -> Classify project size with reasoning")
    print("  2. Send parsed HLD to AI estimation engine")
    print("     -> AI adjusts PERF activity units based on risk factors")
    print("     -> Provides reasoning for each adjustment")
    print("  3. Post estimation report to Jira PET ticket")
    print("  4. Draft .ics meeting invite with PM from reporter field")

    print("\n  PHASE 2 - After NFR meeting:")
    print("  5. Send transcript to AI for intelligent NFR extraction")
    print("     -> Goes beyond regex: understands context, implied requirements")
    print("     -> Scores meeting coverage quality, identifies gaps")
    print("  6. AI re-estimates with NFR data (may adjust from Phase 1)")
    print("  7. AI generates follow-up questions for uncovered areas")
    print("  8. AI writes test plan content (not template-based)")
    print("     -> Each section references actual project components")
    print("  9. Renders test plan as PDF")

    print(f"\n  Sample HLD has {len(SAMPLE_HLD.splitlines())} lines")
    print(f"  Sample transcript has {len(SAMPLE_TRANSCRIPT.splitlines())} lines")

    print("\n  To run with real AI, set Azure OpenAI environment variables.")


if __name__ == "__main__":
    main()
