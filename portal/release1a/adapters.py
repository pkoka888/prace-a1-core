"""Account policy for the invitation-only synthetic review environment."""

from allauth.account.adapter import DefaultAccountAdapter


class InvitationOnlyAccountAdapter(DefaultAccountAdapter):
    """Reviewer accounts are created by the operator invitation flow only."""

    def is_open_for_signup(self, request):
        return False
