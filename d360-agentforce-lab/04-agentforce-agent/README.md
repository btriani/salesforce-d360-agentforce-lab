# Phase 4: Agentforce Agent Design

## Concept

An Agentforce agent grounded in D360's unified data — the "last mile" where data becomes action.

**Without D360:** The agent only sees CRM data (Accounts, Contacts, Opportunities).
**With D360:** The agent sees the full picture — CRM + web engagement + product usage + firmographic enrichment.

## Planned Agent Architecture

### Prompt Template

```
You are a Customer Success advisor with access to the full customer profile.

Account: {Account.Name} ({Account.Industry})
Health Score: {CalculatedInsight.CustomerHealthScore}
Segment: {Segment.Membership} (At Risk / Upsell Ready / Healthy)

Recent Activity:
- Open Cases: {Case.OpenCount} (Highest Priority: {Case.MaxPriority})
- Web Engagement: {WebAnalytics.PageViews30d} page views, {WebAnalytics.DemoPageVisits} demo visits
- Product Usage: {ProductUsage.FeatureAdoptionScore}/100, {ProductUsage.ActiveUsers} active users
- Last Login: {ProductUsage.LastLoginDate}
- Pipeline: {Opportunity.OpenDeals} open deals worth {Opportunity.TotalAmount}

Based on this unified profile, provide:
1. Account health assessment
2. Key risks or opportunities
3. Recommended next-best-action
```

### Agent Actions

| Action | What It Does | D360 Data Used |
|--------|-------------|----------------|
| Account Briefing | "Brief me on {Account}" | Unified profile from all 7 sources |
| At Risk Accounts | "Which accounts need attention?" | Segment: At Risk |
| Next Best Action | "What should I do about {Account}?" | Health Score + Segment + Activity |
| Upsell Candidates | "Who's ready for an upsell?" | Segment: Upsell Ready |

### D360 Concepts

- **Grounded in unified data:** The agent's context includes data from ALL sources, not just CRM
- **Calculated Insights feed the agent:** Health Score is a D360 Calculated Insight combining CRM + external signals
- **Segments drive actions:** "At Risk" and "Upsell Ready" segments are D360 segments built on the unified data model
- **Trust layer:** Agentforce uses the Einstein Trust Layer — the agent can only access data the user has permission to see

## Interview Talking Points

- "An Agentforce agent without D360 is limited to CRM data. With D360, it sees web engagement dropping, product usage declining, AND open support tickets — that's a completely different risk signal than just looking at the pipeline."
- "The Calculated Insight (Health Score) combines signals that live in 4 different systems. Without D360, someone would have to manually correlate these — or they'd miss the pattern entirely."
- "Agentforce's value proposition is directly proportional to the breadth of data it's grounded in. D360 is what makes Agentforce enterprise-grade."
