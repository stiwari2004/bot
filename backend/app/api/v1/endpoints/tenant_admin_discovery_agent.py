"""
Tenant Admin Discovery — agent download endpoints (run script, zip, tarball)
"""
import io
import os
import tarfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _get_discovery_agent_dir() -> Path:
    """Return discovery-agent directory path; raises HTTPException if not found."""
    this_file = Path(__file__).resolve()
    paths_to_try = []
    if os.environ.get("DISCOVERY_AGENT_DIR"):
        paths_to_try.append(Path(os.environ["DISCOVERY_AGENT_DIR"]))
    paths_to_try.append(Path("/app/discovery-agent"))
    app_dir = this_file.parent.parent.parent.parent  # app.api.v1.endpoints -> app
    paths_to_try.append(app_dir / "static" / "discovery_agent")
    backend = this_file.parent.parent.parent.parent.parent
    repo_root = backend.parent
    paths_to_try.append(repo_root / "discovery-agent")
    paths_to_try.append(app_dir.parent.parent / "discovery-agent")
    cwd = Path(os.getcwd())
    paths_to_try.append(cwd / "discovery-agent")
    paths_to_try.append(cwd.parent / "discovery-agent")
    for path in paths_to_try:
        if path.is_dir() and (path / "run_discovery.py").is_file():
            return path
    raise HTTPException(
        status_code=404,
        detail="Discovery agent package not available. Please ensure discovery-agent folder exists."
    )


def _should_skip(f: Path) -> bool:
    """Return True for files that should be excluded from agent archives."""
    if any(part.startswith(".") and part not in [".yaml", ".yml"] for part in f.parts):
        return True
    if ".git" in f.parts or "__pycache__" in f.parts or ".pyc" in f.name:
        return True
    return False


@router.get("/run", response_class=PlainTextResponse)
async def get_run_script():
    """Returns the one_step.py discovery script."""
    try:
        this_file = Path(__file__).resolve()
        backend = this_file.parent.parent.parent.parent.parent
        repo_root = backend.parent
        candidates = [
            repo_root / "discovery-agent" / "one_step.py",
            this_file.parent.parent.parent.parent / "static" / "discovery" / "one_step.py",
            Path(os.getcwd()) / "discovery-agent" / "one_step.py",
        ]
        for script_path in candidates:
            if script_path.is_file():
                return PlainTextResponse(script_path.read_text(encoding="utf-8"), media_type="text/plain")
    except Exception as e:
        logger.error(f"Failed to locate discovery script: {e}", exc_info=True)
    raise HTTPException(
        status_code=404,
        detail="Discovery run script not available. Please download agent.zip or use manual setup."
    )


@router.get("/agent.zip", response_class=Response)
async def get_agent_zip():
    """Returns discovery-agent folder as a zip archive."""
    try:
        agent_dir = _get_discovery_agent_dir()
        logger.info("Found discovery-agent at: %s", agent_dir)
        buf = io.BytesIO()
        files_added = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in agent_dir.rglob("*"):
                if f.is_file() and not _should_skip(f):
                    try:
                        zf.write(f, f.relative_to(agent_dir.parent))
                        files_added += 1
                    except Exception as e:
                        logger.warning(f"Failed to add {f} to zip: {e}")
        if files_added == 0:
            raise HTTPException(status_code=500, detail="Failed to create discovery agent package")
        buf.seek(0)
        logger.info(f"Created agent.zip with {files_added} files, size: {len(buf.getvalue())} bytes")
        return Response(
            content=buf.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=discovery-agent.zip"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent.zip: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create discovery agent package: {str(e)}")


@router.get("/agent.tar.gz", response_class=Response)
async def get_agent_tarball():
    """Returns discovery-agent as .tar.gz archive."""
    try:
        agent_dir = _get_discovery_agent_dir()
        logger.info("Found discovery-agent at: %s", agent_dir)
        buf = io.BytesIO()
        files_added = 0
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for f in agent_dir.rglob("*"):
                if f.is_file() and not _should_skip(f):
                    try:
                        tf.add(f, arcname=f.relative_to(agent_dir.parent))
                        files_added += 1
                    except Exception as e:
                        logger.warning("Failed to add %s: %s", f, e)
        if files_added == 0:
            raise HTTPException(status_code=500, detail="Failed to create discovery agent package")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/gzip",
            headers={"Content-Disposition": "attachment; filename=discovery-agent.tar.gz"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating agent.tar.gz: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create discovery agent package")
