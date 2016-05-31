from ecs import bootstrap
from ecs.utils import Args
from ecs.votes.models import Vote
from ecs.votes.workflow import VoteReview, VoteSigning, is_final
from ecs.integration.utils import setup_workflow_graph
from ecs.workflow.patterns import Generic


# dummy gettext
_ = lambda s: s

@bootstrap.register(depends_on=('ecs.integration.bootstrap.workflow_sync', 'ecs.core.bootstrap.auth_groups'))
def vote_workflow():
    EXECUTIVE_GROUP = 'EC-Executive Board Member'
    OFFICE_GROUP = 'EC-Office'
    INTERNAL_REVIEW_GROUP = 'EC-Internal Reviewer'
    SIGNING_GROUP = 'EC-Signing'

    setup_workflow_graph(Vote, 
        auto_start=True, 
        nodes={
            'start': Args(Generic, start=True, name=_("Start")),
            'executive_vote_review': Args(VoteReview, name=_("Executive Vote Review"), group=EXECUTIVE_GROUP),
            'internal_vote_review': Args(VoteReview, name=_("Internal Vote Review"), group=INTERNAL_REVIEW_GROUP),
            'office_vote_finalization': Args(VoteReview, name=_("Office Vote Finalization"), group=OFFICE_GROUP),
            'final_office_vote_review': Args(VoteReview, name=_("Office Vote Review"), group=OFFICE_GROUP),
            'vote_signing': Args(VoteSigning, group=SIGNING_GROUP, name=_("Vote Signing")),
        }, 
        edges={
            ('start', 'office_vote_finalization'): None,
            ('office_vote_finalization', 'internal_vote_review'): None,

            ('internal_vote_review', 'office_vote_finalization'): Args(guard=is_final, negated=True),
            ('internal_vote_review', 'executive_vote_review'): Args(guard=is_final),

            ('executive_vote_review', 'final_office_vote_review'): Args(guard=is_final, negated=True),
            ('executive_vote_review', 'vote_signing'): Args(guard=is_final),
            
            ('final_office_vote_review', 'executive_vote_review'): None,
        }
    )

