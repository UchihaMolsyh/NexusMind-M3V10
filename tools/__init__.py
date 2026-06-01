"""NexusMind Tools Package — auto-registers all tools on import."""

def register_all_tools():
    """Import all tool modules to trigger registration."""
    from tools import (
        core_tools,
        math_physics, physics_sim, monte_carlo, bayesian,
        file_io, python_exec, sql_db, git_tools, github_tools,
        osint, virus_scan, image_proc, image_gen, video_gen,
        speech, audio, static_analysis, stoch_analysis,
        model_tools, model_3d, motion_tracking,
        system_tools,
        # New AI/ML tools
        rag_tools, reasoning_tools, workflow_tools,
        data_tools, eval_tools, ml_tools,
        infra_tools, browser_tools, doc_tools,
    )

