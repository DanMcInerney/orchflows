"""Freeze the authored recipe, then exercise two fresh independent consumers."""
import asyncio


async def run(trial):
    authored = await trial.invoke('author', timeout=840)
    stage = trial.stages[-1]
    if stage['execution']['status'] != 'completed' or not stage['native'].get('terminal_success'):
        trial.gaps.append('Authoring did not complete; fresh reuse was not started.')
        return
    library = trial.freeze(authored / '.orchflows/libraries/personal', 'personal')
    request = ('Use requests.json in this workspace to produce plan.json and brief.md '
               'directly in the workspace root (./plan.json and ./brief.md). '
               'Apply the saved weekly-plan workflow and its declared guidance. '
               'Preserve inputs and packages. No network, installation, messages, purchases or global registration. '
               'Use at most four child agents. Report checks and unresolved gaps.')
    await asyncio.gather(*(
        trial.invoke(name, entrypoint='personal:weekly-plan',
                     packages={'personal': library}, fixtures=trial.case.path / 'reuse' / name,
                     request=request, timeout=240)
        for name in ('changed', 'empty')))
