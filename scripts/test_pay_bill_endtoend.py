import asyncio
import os
import sys
import time

# ensure project root on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.agent_orchestrator import ArvynOrchestrator

async def run_test():
    orch = ArvynOrchestrator()
    # Ensure browser starts
    await orch.browser.start()

    # Provide test credentials in profile (temporary)
    orch.profile.update_provider('Rio Finance Bank', {
        'login_credentials': {'email': 'testuser@example.com', 'password': 'P@ssw0rd!'}
    })

    state = {
        'messages': [],
        'intent': {'action': 'PAY_BILL', 'provider': 'Rio Finance Bank'},
        'user_data': {},
        'task_history': [],
        'current_step': '',
        'browser_context': {},
        'screenshot': None,
        'pending_question': None,
        'transaction_details': {},
        'human_approval': None,
        'error_count': 0
    }

    print('Navigating to provider site...')
    await orch._node_site_discovery(state)
    print('Running autonomous executor for PAY_BILL...')
    result = await orch._node_autonomous_executor(state)
    print('Result:')
    print(result)

    # cleanup
    await orch.cleanup()

if __name__ == '__main__':
    asyncio.run(run_test())
