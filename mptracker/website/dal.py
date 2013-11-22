from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from jinja2 import filters
from mptracker.models import (
    Person,
    Mandate,
    MpGroup,
    MpGroupMembership,
    Proposal,
    ProposalActivityItem,
    Sponsorship,
    Transcript,
    Question,
    Ask,
    VotingSession,
    Vote,
    PolicyDomain,
)


class DataAccess:

    def search_person(self, query):
        sql_query = (
            Person.query
            .join(Person.mandates)
            .filter_by(year=2012)
            .filter(func.lower(Person.name).like('%' + query.lower() + '%'))
            .order_by(Person.name)
        )
        return [
            {'name': person.name, 'id': person.id}
            for person in sql_query.all()
        ]

    def get_person(self, person_id, missing=KeyError):
        person = Person.query.get(person_id)
        if person is None:
            raise missing()
        return {'name': person.name}

    def get_mandate2012_details(self, person_id):
        mandate = (
            Mandate.query
            .filter_by(person_id=person_id)
            .filter_by(year=2012)
            .first()
        )

        membership_query = (
            mandate.group_memberships
            .order_by(MpGroupMembership.interval.desc())
        )
        group_history = [
            {
                'start_date': membership.interval.lower,
                'end_date': membership.interval.upper,
                'role': membership.role,
                'group_short_name': membership.mp_group.short_name,
                'group_id': membership.mp_group_id,
            }
            for membership in membership_query
        ]

        rv = {'group_history': group_history}

        if mandate.county:
            rv['college'] = {
                'county_name': mandate.county.name,
                'number': mandate.college,
            }

        voting_session_count = (
            VotingSession.query
            .filter(VotingSession.final == True)
            .count()
        )
        final_votes = (
            mandate.votes
            .join(Vote.voting_session)
            .filter(VotingSession.final == True)
        )
        votes_attended = final_votes.count()
        votes_loyal = final_votes.filter(Vote.loyal == True).count()

        rv['vote'] = {
            'attendance': votes_attended / voting_session_count,
            'loyalty': votes_loyal / votes_attended,
        }

        rv['speeches'] = mandate.transcripts.count()
        rv['proposals'] = mandate.sponsorships.count()

        rv['recent_activity'] = self._get_recent_activity(mandate)

        return rv

    def _get_recent_activity(self, mandate):
        recent_transcripts_query = (
            mandate.transcripts
            .order_by(Transcript.serial.desc())
            .limit(5)
            .options(joinedload('chapter'))
        )
        recent_transcripts = [
            {
                'date': t.chapter.date,
                'text': filters.do_truncate(t.text, 200),
                'type': 'speech',
            }
            for t in recent_transcripts_query
        ]

        recent_questions_query = (
            Question.query
            .join(Question.asked)
            .filter(Ask.mandate == mandate)
            .order_by(Question.date.desc())
            .limit(5)
        )
        recent_questions = [
            {
                'date': q.date,
                'text': filters.do_truncate(q.title),
                'type': q.type,
            }
            for q in recent_questions_query
        ]

        recent_proposals_query = (
            Proposal.query
            .join(Proposal.sponsorships)
            .filter(Sponsorship.mandate == mandate)
            .order_by(Proposal.date.desc())
            .limit(5)
        )
        recent_proposals = [
            {
                'date': p.date,
                'text': p.title,
                'type': 'proposal',
                'proposal_id': p.id,
            }
            for p in recent_proposals_query
        ]

        rv = recent_transcripts + recent_questions + recent_proposals
        rv.sort(key=lambda r: r['date'], reverse=True)
        return rv[:10]


    def get_party_list(self):
        return [
            {'name': group.name, 'id': group.id}
            for group in MpGroup.query.order_by(MpGroup.name)
            if group.short_name not in ['Indep.', 'Mino.']
        ]

    def get_party_details(self, party_id, missing=KeyError):
        party = MpGroup.query.get(party_id)
        if party is None:
            raise missing()
        rv = {'name': party.name}

        rv['member_list'] = []
        memberships_query = (
            party.memberships
            .filter(
                MpGroupMembership.interval.contains(date.today())
            )
            .options(
                joinedload('mandate'),
                joinedload('mandate.person'),
            )
            .join(MpGroupMembership.mandate)
            .join(Mandate.person)
            .order_by(Person.name)
        )
        for membership in memberships_query:
            person = membership.mandate.person
            rv['member_list'].append({
                'name': person.name,
                'id': person.id,
            })

        final_votes = (
            Vote.query
            .join(Vote.voting_session)
            .filter(VotingSession.final == True)
            .join(Vote.mandate)
            .join(Mandate.group_memberships)
            .filter(MpGroupMembership.mp_group_id == party_id)
        )
        votes_attended = final_votes.count()
        votes_loyal = final_votes.filter(Vote.loyal == True).count()
        rv['member_loyalty'] = votes_loyal / votes_attended

        return rv

    def get_policy_list(self):
        return [
            {'name': policy.name, 'id': policy.id}
            for policy in PolicyDomain.query
        ]

    def get_policy(self, policy_id, missing=KeyError):
        policy = PolicyDomain.query.get(policy_id)
        if policy is None:
            raise missing()
        return {'name': policy.name}

    def get_policy_proposal_list(self, policy_id):
        proposal_query = (
            Proposal.query
            .filter_by(policy_domain_id=policy_id)
        )
        return [
            {'title': proposal.title, 'id': proposal.id}
            for proposal in proposal_query
        ]

    def get_proposal_details(self, proposal_id, missing=KeyError):
        proposal = Proposal.query.get(proposal_id)
        if proposal is None:
            raise missing()
        rv = {'title': proposal.title}

        rv['activity'] = []
        activity_query = (
            proposal.activity
            .order_by(ProposalActivityItem.order.desc())
        )
        for item in activity_query:
            rv['activity'].append({
                'date': item.date,
                'location': item.location.lower(),
                'html': item.html,
            })

        sponsors_query = (
            Person.query
            .join(Person.mandates)
            .join(Mandate.sponsorships)
            .filter(Sponsorship.proposal == proposal)
        )
        rv['sponsors'] = []
        for person in sponsors_query:
            rv['sponsors'].append({
                'name': person.name,
                'id': person.id,
            })

        return rv
