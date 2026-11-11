## Summary

<!-- What changes, and why? -->

## Scope

- [ ] Focused change with one independently reviewable purpose
- [ ] No unrelated formatting, generated files, logs or personal configuration
- [ ] Documentation updated where user-facing behaviour changes

## Compatibility and safety

- [ ] Existing muOS package paths, launcher contracts and configuration keys remain compatible, or migration is documented
- [ ] Optional dependencies remain optional and fail gracefully
- [ ] No blocking network or system commands were added to UI render/update paths
- [ ] Downloaded content, archives and privileged operations are validated

## Validation evidence

- [ ] Relevant automated tests added or updated
- [ ] Python checks / repository integrity audit passed where applicable
- [ ] Shell and Lua checks passed where applicable
- [ ] Build/package validation passed where applicable
- [ ] Physical device test completed, or explicitly marked as still required

**Commands and results:**

<!-- Paste concise test evidence. Do not claim hardware validation from CI. -->

**Devices / firmware / frontend tested:**

<!-- Exact model, firmware version and Pygame/LÖVE frontend. -->

## Risk and rollout

**User-visible effect:**

**Known limitations / follow-up issues:**

**Rollback considerations:**
