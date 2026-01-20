🌎 Available in: [Português](./README.pt-BR.md)

Currículos SaaS — LLM-Powered Resume Analysis Platform

Currículos SaaS is a backend SaaS application designed for resume analysis, comparison, and report generation using Large Language Models (LLMs).
The project focuses on clean architecture, scalability, and real-world SaaS constraints, rather than being a tutorial or proof-of-concept.

Built with FastAPI, the system follows a layered architecture that separates concerns and enables maintainability, testing, and future growth.

Tech Stack

Backend: FastAPI (Python)

LLM Integration: OpenAI API

Database: PostgreSQL (migration from Supabase Free Tier)

ORM: SQLAlchemy (async) + asyncpg

Data Validation: Pydantic

Deployment: Render

Architecture Pattern: Layered Architecture (API → Service → Repository)

System Architecture

The system is designed using a layered backend architecture, clearly separating responsibilities between request handling, business logic, and persistence.

Architectural Layers
API Layer (FastAPI)

Handles HTTP requests from web or external clients

Performs request validation

Delegates execution to the service layer

Service Layer

Contains all business logic

Responsible for OpenAI (LLM) integration

Implements resume analysis, matching logic, and report generation

Domain Layer

Pydantic Schemas (DTOs) for request/response validation

SQLAlchemy Models representing domain entities

Ensures data consistency and structure

Repository Layer

Database access abstraction

SQL queries using SQLAlchemy with asyncpg

Enables easier database replacement and testing

Database

Initially implemented using Supabase (Free Tier)

Planned migration to a dedicated PostgreSQL instance due to SaaS limitations

Database Migration Strategy

During development, limitations of the Supabase Free Tier were identified, including:

Restrictions on complex queries

Constraints affecting SaaS-level operations and scalability

To address this, the project is architected to allow a seamless migration to PostgreSQL, without impacting higher layers of the system.
This is achieved through strict separation between service and repository layers.

Testing Strategy

Unit Tests: Business logic and service validation

Integration Tests: API endpoints and database interactions

Architecture prepared for CI/CD integration

Key Features

Resume upload and analysis

Resume-to-job description matching using LLMs

Structured report generation

Architecture prepared for PDF export

SaaS-ready foundation (multi-tenant friendly)

Local Setup
# Clone the repository
git clone https://github.com/Jgaps7/curriculos-saas.git
cd curriculos-saas

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

Environment Variables
OPENAI_API_KEY=your_api_key
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db

Run the API
uvicorn main:app --reload


Access:

API Documentation (Swagger): http://localhost:8000/docs

Project Purpose

This project was created to demonstrate:

Modern backend architecture with FastAPI

Practical application of LLMs in a SaaS context

Clean separation of concerns and scalability-oriented design

Readiness for production, monetization, and cloud deployment

Author

Julio Alencar
Technology & Automation Specialist
FastAPI • LLMs • APIs • SaaS Architecture

LinkedIn: https://www.linkedin.com/in/juliioalencar/

GitHub: https://github.com/Jgaps7

Project Status

Work in progress.
Core architecture is stable, with continuous improvements planned.

Honest assessment

With this README:

The project is interview-ready

It communicates architectural thinking clearly

It positions you above “tutorial-level” candidates

It aligns well with international backend and SaaS roles

