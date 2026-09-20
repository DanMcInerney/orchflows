"""Freeze the authored package before matched-input and unseen consumers."""
import asyncio


async def run(trial):
    authored = await trial.invoke('author', profile='authoring', timeout=900)
    stage = next(stage for stage in trial.stages if stage['name'] == 'author')
    if stage['execution']['status'] != 'completed' or not stage['native'].get('terminal_success'):
        trial.gaps.append('Authoring did not complete; package freeze and fresh reuse were not started.')
        return
    library = trial.freeze(authored / '.orchflows/libraries/personal', 'personal')
    request = (
        'Use the local changes.json and README.md contract to produce release-notes.md and '
        'migration-checklist.md directly in the workspace root '
        '(./release-notes.md and ./migration-checklist.md). Apply the saved release-brief '
        'workflow and its declared guidance. Preserve inputs and packages. Use only local '
        'source material; no task-facing network access, installation, messages, publishing, '
        'purchases or global registration changes. Use at most four child agents. '
        'Report checks and unresolved gaps.')
    await asyncio.gather(*(
        trial.invoke(name, entrypoint='personal:release-brief',
                     packages={'personal': library}, fixtures=trial.case.path / (
                         'fixtures' if name == 'representative' else 'reuse/' + name),
                     request=request, profile='local', timeout=480)
        for name in ('representative', 'changed', 'sparse')))
