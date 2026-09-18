import asyncio


async def run(trial):
    authored = await trial.invoke('author', timeout=360)
    library = trial.freeze(authored / '.orchflows/libraries/personal', 'personal')
    await asyncio.gather(
        trial.invoke('decision', entrypoint='personal:decision-brief', packages={'personal': library},
                     fixtures=trial.case.path / 'reuse/decision', timeout=150,
                     request='Use offers.json in this workspace. Write brief.json and required intermediate evidence here. '
                             'Apply the saved workflow and personal guidance; do not change the library. No external actions.'),
        trial.invoke('component', entrypoint='personal:summarize-offers', packages={'personal': library},
                     fixtures=trial.case.path / 'reuse/component', timeout=90,
                     request='Summarize offers.json into summary.json here using this component and its guidance. '
                             'Do not run the larger decision workflow or change the library. No external actions.'))
