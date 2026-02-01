"""Greenhouse tool registration."""

from typing import TYPE_CHECKING
from fastmcp import FastMCP

from .greenhouse import GreenhouseClient

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialManager


def register_tools(mcp: FastMCP, credentials: "CredentialManager | None" = None) -> None:
    """Register Greenhouse tools with the MCP server."""
    client = None

    def get_client() -> GreenhouseClient:
        nonlocal client
        if client is None:
            api_key = credentials.get("greenhouse_api_key") if credentials else None
            # Fallback to os.getenv if credentials manager not used
            client = GreenhouseClient(api_key=api_key)
        return client

    @mcp.tool()
    def greenhouse_list_jobs(
        limit: int = 50,
        status: str = "open",  # open, closed, draft
        department_id: int | None = None,
        office_id: int | None = None,
    ) -> list[dict]:
        """
        List job postings with filters.

        Args:
            limit: Maximum number of jobs to return (default: 50)
            status: Filter by job status: 'open' (default), 'closed', 'draft'
            department_id: Filter by department ID
            office_id: Filter by office/location ID
        """
        return get_client().list_jobs(
            limit=limit,
            status=status,
            department_id=department_id,
            office_id=office_id,
        )

    @mcp.tool()
    def greenhouse_get_job(job_id: int) -> dict:
        """
        Get detailed job information.

        Args:
            job_id: The ID of the job to retrieve
        """
        return get_client().get_job(job_id)

    @mcp.tool()
    def greenhouse_list_candidates(
        limit: int = 50,
        job_id: int | None = None,
        stage: str | None = None,
        created_after: str | None = None,
        updated_after: str | None = None,
    ) -> list[dict]:
        """
        List candidates with filters.

        Args:
            limit: Maximum number of candidates to return (default: 50)
            job_id: Filter by job application
            stage: Filter by current stage name (e.g., 'Initial Screen')
            created_after: ISO 8601 date string (e.g., '2023-01-01T00:00:00Z')
            updated_after: ISO 8601 date string
        """
        return get_client().list_candidates(
            limit=limit,
            job_id=job_id,
            stage=stage,
            created_after=created_after,
            updated_after=updated_after,
        )

    @mcp.tool()
    def greenhouse_get_candidate(candidate_id: int) -> dict:
        """
        Get full candidate details including applications and activity.

        Args:
            candidate_id: The ID of the candidate
        """
        return get_client().get_candidate(candidate_id)

    @mcp.tool()
    def greenhouse_add_candidate(
        first_name: str,
        last_name: str,
        email: str,
        job_id: int,
        phone: str | None = None,
        source: str | None = None,
        resume_url: str | None = None,
        notes: str | None = None,
    ) -> dict:
        """
        Submit a new candidate to the pipeline for a specific job.

        Args:
            first_name: Candidate's first name
            last_name: Candidate's last name
            email: Candidate's primary email
            job_id: ID of the job to apply to
            phone: Optional phone number
            source: Source of the candidate (e.g., 'LinkedIn', 'Referral')
            resume_url: URL to resume file (PDF/Doc)
            notes: Initial notes to add to candidate profile
        """
        return get_client().add_candidate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            job_id=job_id,
            phone=phone,
            source=source,
            resume_url=resume_url,
            notes=notes,
        )

    @mcp.tool()
    def greenhouse_list_applications(
        job_id: int,
        limit: int = 50,
        status: str | None = None,  # active, rejected, hired
    ) -> list[dict]:
        """
        List applications for a specific job.

        Args:
            job_id: The job to list applications for
            limit: Maximum applications to return
            status: Filter by status: 'active', 'rejected', 'hired'
        """
        return get_client().list_applications(
            job_id=job_id,
            limit=limit,
            status=status,
        )
