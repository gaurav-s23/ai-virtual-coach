# Cleanup Notes for AI Virtual Coach Project

## Files Considered for Removal

### Documentation Files
- `backend/technical_log.md` - Development log file, can be removed in production
- `system_deep_dive.md` - Deep analysis document, keep for reference
- `LOCAL_SETUP.md` - Local setup instructions, keep for developers

### Test Files
The following test files in `backend/` may be outdated and should be reviewed:
- `test_auth_and_persistence.py`
- `test_api.py` 
- `test_bugfixes_regression.py`
- `test_rag_and_llm.py`

**Recommendation**: Keep test files but review and update as needed for current functionality.

### Compatibility Files
- `backend/llm_service.py` - This is a compatibility shim that imports from `services/llm_service.py`
- **Status**: Keep this file as it provides backward compatibility

## Recommended Cleanup Actions

1. **Safe to remove**:
   - `backend/technical_log.md` (development log)
   - Any temporary debug files
   - `debug-*.log` files

2. **Review and update**:
   - Test files to ensure they match current API
   - Documentation files for accuracy

3. **Keep**:
   - All core application files
   - Configuration files
   - Main documentation (README.md, TECHNICAL_DOCS.md)
   - Compatibility shims

## Docker Volumes
The following volumes are created and may consume disk space:
- `postgres_data`
- `chroma_data` 
- `backend_chroma`
- `backend_hf_cache`
- `frontend_node_modules`

Use `docker volume prune` to clean up unused volumes if needed.
