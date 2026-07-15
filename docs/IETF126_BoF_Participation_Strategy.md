# IETF 126 BoF Participation Strategy — AGL Governance Extension

**Prepared:** 2026-07-15 | **Meeting:** IETF 126, Vienna, 18–24 July 2026
**Venue:** Hilton Vienna Park | **BoF Room:** Grand Park Hall 3
**Remote Participation:** Available via Meetecho (free option per RFC 9501)
**Registration:** https://registration.ietf.org/126/

---

## Executive Summary

IETF 126 features three Agent-related BoFs that represent the IETF community's most significant engagement with AI agent standardization to date. The Agent Protocol Governance Extension (APGE) proposed by BDE Score addresses a specific, well-defined gap — immutable compliance receipts with drift-aware governance — that none of the existing I-Ds in this space cover. Our strategy is to position APGE as a **composable extension** rather than a competing protocol, emphasizing three differentiators: (1) drift-aware model-state commitments, (2) multi-jurisdictional regulatory binding (EU + China), and (3) MCP extension framework integration. The goal across all three BoFs is to build awareness, identify potential co-authors, and secure a path for APGE as a referenced extension in whichever Working Group(s) emerge.

---

## 1. DAWN BoF — Discovery of Agents, Workloads, and Named Entities

**Date/Time:** Tuesday, 21 July 2026, 14:00–16:00 CEST
**Format:** WG-forming BoF
**Mailing List:** dawn@ietf.org (active discussion underway)
**Key Participants to Watch:** Nick Williams (DNS-AID proponent), Adrian Farrel (CATALIST chair)
**Charter Direction:** Developing requirements and protocol solutions for automated, decentralized, interoperable discovery of AI agents and workloads at scale.

### 1.1 Relevance to APGE

DAWN's problem statement explicitly includes compliance features in discovery:
> "Discovery protocols MUST provide mechanisms to ensure high availability...auditability MUST be supported through verifiable logging of discovery and registration events" [(draft-mozley-aidiscovery-00)](https://www.ietf.org/archive/id/draft-mozley-aidiscovery-00.html)

This means the DAWN charter will likely include audit/compliance as a normative requirement for any discovery mechanism. APGE's governance receipts are a natural complement: when an agent is discovered, the discovery event itself should produce a compliance receipt.

### 1.2 Speaking Points

**Primary intervention (2-3 minutes):**

1. **Acknowledge the compliance requirement in the problem statement.** The draft correctly identifies that "auditability MUST be supported through verifiable logging of discovery and registration events." This is not optional — EU AI Act Art. 12 requires automated record-keeping, and China's agent governance regulation (effective today, 15 July 2026) requires agent identity registration with designated authorities.

2. **Introduce the gap.** Current discovery proposals (DNS-AID, agent:// URI, centralized registries) focus on *finding* agents. None addresses the question: *how does a relying party verify that the discovered agent's governance state was valid at discovery time?* Discovery without governance verification creates a trust gap — you can find the agent, but you cannot verify it was operating under compliant governance when you found it.

3. **Propose a governance receipt binding for discovery events.** We have an implementation (APGE) that generates immutable compliance receipts anchored to a transparency log for every governance event. When an agent is discovered, the discovery response could carry a receipt reference proving the agent was under compliant governance at discovery time. This is a cross-cutting concern — it does not require changes to the discovery protocol itself, but it does require the discovery protocol to carry or reference receipt identifiers.

4. **Offer collaboration.** We are happy to work with the DAWN community to define a governance-receipt binding for whatever discovery mechanism emerges. This could be as simple as a well-known URL pattern or a field in the agent descriptor.

**Follow-up on the mailing list (within 24 hours):**

- Post a concise (300-word) message to dawn@ietf.org with subject "Governance Receipt Binding for Agent Discovery — a cross-cutting concern"
- Reference the compliance requirements in the problem statement
- Link to APGE draft (once published on Datatracker)
- Offer to co-author a discovery-governance binding section in the DAWN requirements document

### 1.3 Key People to Connect With

| Person | Affiliation | Why |
|---|---|---|
| Nick Williams | DNS-AID proponent | Leading discovery approach; needs compliance layer |
| Adrian Farrel | CATALIST/DAWN chair | Gatekeeper for what enters the charter |
| Ying-Zhen Qu | CATALIST co-chair | Coordination with broader agent efforts |
| Suresh Krishnan | Former IETF AD | Presented external coordination summary at CATALIST |

### 1.4 Risk Assessment

- **Risk:** DAWN charter may be too narrowly scoped (discovery-only) to include governance.
- **Mitigation:** Frame APGE as an *external* dependency, not a charter deliverable. Discovery protocols reference governance receipts; they do not define them.
- **Risk:** DNS-AID proponents may resist adding governance metadata to DNS responses.
- **Mitigation:** Governance receipts are referenced by URL/ID, not embedded in DNS. The DNS response carries a pointer; the receipt is resolved separately.

---

## 2. DMSC BoF — Dynamic Multi-Agent Secured Collaboration

**Date/Time:** Wednesday, 22 July 2026, 09:00–11:00 CEST
**Format:** Non-WG-forming BoF (temperature-check)
**Mailing List:** dmsc@ietf.org (active discussion)
**Key Participants to Watch:** Huiyuan (Adrian) Li (DMSC presenter at CATALIST), X. Li (MACP lead author, China Telecom), B. Liu (Huawei)
**Key Drafts:** draft-li-dmsc-macp-04 (MACP architecture), draft-zhang-dmsc-mas-communication-00 (security analysis), draft-cui-dmsc-agent-cdi-00 (cross-domain interoperability)

### 2.1 Relevance to APGE

DMSC is the highest-value BoF for APGE because:

1. **MACP's Agent Gateway (AGW) is a natural integration point.** The AGW mediates all inter-agent communication and is responsible for "policy control, observability, and secure communication" [(draft-li-dmsc-macp-04)](https://www.ietf.org/archive/id/draft-li-dmsc-macp-04.html). APGE governance receipts are generated at exactly this layer.

2. **DMSC's security analysis explicitly identifies the governance gap.** draft-zhang-dmsc-mas-communication-00 notes that "existing Internet protocols...were not designed for agent-native semantics such as dynamic identity, computation-bounded requests, context integrity, and intermediary trust" [(draft-zhang-dmsc)](https://www.ietf.org/archive/id/draft-zhang-dmsc-mas-communication-00.txt). APGE addresses "context integrity" through drift-aware governance.

3. **Cross-domain interoperability requires compliance evidence.** draft-cui-dmsc-agent-cdi-00 defines a framework for cross-domain agent collaboration with "Auditability: All cross-domain interactions are logged and auditable" [(draft-cui)](https://www.ietf.org/archive/id/draft-cui-dmsc-agent-cdi-00.html). APGE provides the tamper-evident, cryptographically verifiable audit mechanism this requires.

4. **DMSC is non-WG-forming.** This means there is no fixed charter to work within, and the community is explicitly seeking input on what should be standardized. This is the best opportunity to shape requirements.

### 2.2 Speaking Points

**Primary intervention (3-4 minutes):**

1. **Start with the security gap analysis.** The MACP security analysis correctly identifies that existing protocols lack agent-native semantics. I want to add one more gap to the list: **governance observability at the gateway layer.** The AGW is responsible for policy enforcement, but the current drafts do not specify how policy enforcement decisions are recorded, how they can be audited after the fact, or how a relying party can verify that enforcement occurred.

2. **Present the drift-aware governance concept.** In a multi-agent system, an agent's behavior depends on its model state. If the model changes between authorization and execution — configuration drift, model substitution, tool inventory changes — the authorization is no longer valid. We call this "governance drift" and we have implemented a drift-detection mechanism in our APGE extension. When drift is detected, the original governance receipt is invalidated and a drift_alert receipt is generated.

3. **Show the AGW integration.** APGE integrates with the MACP AGW as follows:
   - Every inter-agent message passing through the AGW is evaluated against applicable governance policies.
   - A governance receipt is generated before the message is forwarded.
   - The receipt is anchored to a transparency log aligned with RFC 9162 (Certificate Transparency) and RFC 9943 (SCITT).
   - If drift is detected between the agent's declared state and its actual state, the message is blocked and a drift_alert is issued.
   - The receipt identifier is propagated via W3C Trace Context for cross-protocol correlation.

4. **Emphasize regulatory urgency.** EU AI Act Art. 50 enforcement begins on 2 August 2026 — 12 days after this BoF. China's agent governance regulation is already in force. Any multi-agent collaboration framework that cannot produce tamper-evident compliance records will face deployment barriers in both jurisdictions.

5. **Propose a specific work item.** We propose adding a "Governance Receipt Binding" section to the MACP architecture document that specifies how the AGW generates, anchors, and propagates governance receipts for inter-agent operations. We are prepared to contribute text.

**Secondary intervention (if discussion allows):**

- Respond to any discussion about the Agent Management Center (AMC) by noting that the AMC's identity lifecycle management (Agent Registration Protocol, Agent Authentication and Authorization Protocol) should produce governance receipts for registration and authentication events, not just for tool invocations. This creates a complete audit trail from onboarding through operation.

### 2.3 Key People to Connect With

| Person | Affiliation | Why |
|---|---|---|
| X. Li | China Telecom | Lead author of MACP; direct collaboration on AGW integration |
| B. Liu | Huawei Technologies | MACP co-author; industry weight |
| Huiyuan (Adrian) Li | DMSC originator | Presenter; can shape BoF direction |
| Y. Cui | Tsinghua University | Cross-domain interoperability; needs compliance audit |
| H. Zhang | China Telecom | Security analysis author; needs governance gap filled |

### 2.4 Strategic Note: China Telecom / Huawei Authors

The MACP authors (China Telecom, Huawei) are key targets for APGE adoption because:

1. China's agent governance regulation creates immediate compliance requirements for Chinese operators.
2. APGE's `cn-agent-governance` compliance profile directly addresses these requirements.
3. The AGW architecture in MACP is designed for centralized policy enforcement — APGE adds the missing audit trail.
4. **Action:** Request a side meeting with X. Li and B. Liu to discuss AGW+APGE integration. Offer to co-author a governance receipt section in the next MACP revision.

### 2.5 Risk Assessment

- **Risk:** DMSC may not form a WG, leaving APGE without a formal home.
- **Mitigation:** Build relationships with MACP authors regardless of WG formation. APGE can progress as an individual I-D referenced by MACP.
- **Risk:** Chinese participants may be cautious about engaging with compliance extensions that reference EU regulation.
- **Mitigation:** Emphasize APGE's multi-jurisdictional design. The `cn-agent-governance` profile demonstrates that APGE is not EU-centric.

---

## 3. agentproto BoF — Agent Communication Protocols

**Date/Time:** Thursday, 23 July 2026, 09:00–11:00 CEST
**Format:** WG-forming BoF
**Mailing List:** agentproto@ietf.org (or the list referenced from Datatracker)
**Key Participants to Watch:** Jonathan Rosenberg (framework lead), Cullen Jennings (framework lead), David Schinazi (advised tight scoping at CATALIST), Andy Newton (ART AD)
**Charter Direction:** Identify which building blocks of agent-to-agent and agent-to-tool communication genuinely need to be standardized; charter a WG to take that work forward.

### 3.1 Relevance to APGE

agentproto is the most important BoF for APGE's long-term positioning because:

1. **The charter explicitly includes "confirmation evidence" as a building block.** The agentproto charter scope includes "independent agent identity, fine-grained operation-bound authorization, delegated authorization across agent chains, **confirmation evidence**, durable sessions, recovery, and point-to-multipoint communication" [(agentica.wiki)](https://agentica.wiki/articles/agent-communication-protocols). APGE governance receipts are a form of confirmation evidence.

2. **Rosenberg's framework positions agent protocols as a new layer.** The framework draft [AIPROTO] asks "Are AI Protocols the next layer of the modern IP Protocol Stack?" and identifies governance as a cross-cutting concern. APGE fits naturally as a governance sub-layer.

3. **The WG charter will determine what is in-scope.** If governance/audit is explicitly included in the charter, APGE has a home. If it is out-of-scope, APGE must be positioned as an external extension.

4. **MCP, A2A, and AGTP are all in the room.** agentproto is where the overlapping protocols converge. APGE's protocol-agnostic design is a selling point here — it works across all of them.

### 3.2 Speaking Points

**Primary intervention (3-4 minutes):**

1. **Support the charter scope and add one item.** The proposed charter correctly identifies the key building blocks. I want to argue that "confirmation evidence" should be understood broadly enough to include **compliance confirmation** — not just technical confirmation that a message was delivered, but cryptographic evidence that the operation was governed by the appropriate policies before execution.

2. **Present the gap.** The current I-D landscape has:
   - DRP [(draft-nelson)](https://www.ietf.org/archive/id/draft-nelson-agent-delegation-receipts-00.txt) — user-to-operator delegation receipts
   - PoB [(draft-dembowski)](https://www.ietf.org/archive/id/draft-dembowski-agentledger-proof-of-behavior-00.txt) — behavioral audit receipts
   - ACTA [(draft-farley)](https://www.ietf.org/archive/id/draft-farley-acta-signed-receipts-00.txt) — MCP-specific access control receipts
   - ASQAV [(draft-marques)](https://www.ietf.org/archive/id/draft-marques-asqav-compliance-receipts-00.html) — EU AI Act compliance profile of ACTA
   - AGTP-LOG [(draft-hood)](https://www.ietf.org/archive/id/draft-hood-agtp-log-02.txt) — transparency log for AGTP
   
   These are fragmented. Each addresses a part of the problem (delegation, behavior, access control, compliance, identity audit) but none provides a unified, drift-aware, multi-jurisdictional receipt schema that works across all AGMPs.

3. **Introduce APGE as a unifying extension.** We propose the Agent Protocol Governance Extension (APGE), which:
   - Provides a unified, drift-aware receipt schema that composes with any AGMP
   - Integrates with MCP's new Extensions framework (io.bdescore/apge)
   - Binds to W3C Trace Context for cross-protocol correlation
   - Supports multi-jurisdictional compliance profiles (EU AI Act + China governance)
   - Anchors to a transparency log aligned with RFC 9162 / RFC 9943
   - Is designed to be referenced by, not replace, existing receipt drafts

4. **Ask the room a question.** "Given that at least five I-Ds already address pieces of the agent governance/receipt problem, is there interest in the agentproto WG charter explicitly including 'governance extension' or 'compliance confirmation evidence' as a work item, with the understanding that it would be a protocol-agnostic extension composable with any AGMP?"

**Secondary intervention (if discussion turns to scope):**

- If David Schinazi or others argue for tight scoping (as they did at CATALIST, advising "the IETF is most successful with small, tightly scoped deliverables"), agree but argue that governance extension is **exactly** the kind of small, tightly scoped deliverable that works: it does not define a new protocol, it does not change wire formats, it adds a composable extension layer. This is the same approach MCP 2026-07-28 takes with its Extensions framework.

### 3.3 Key People to Connect With

| Person | Affiliation | Why |
|---|---|---|
| Jonathan Rosenberg | Five9 | Framework lead; shapes charter scope |
| Cullen Jennings | Cisco/IETF | Framework co-lead; "godfather" of agent proto work |
| David Schinazi | Google | Advocates tight scoping; needs to see APGE is narrow |
| Andy Newton | ART AD | Decides charter approval |
| Paul Hoffman | IETF veteran | Cautioned against broad scope at CATALIST; needs narrow pitch |
| C. Hood | Nomotic (AGTP author) | AGTP-LOG already uses CT/SCITT; natural ally |

### 3.4 Strategic Note: AGTP Alliance

C. Hood (AGTP author) is the most natural ally for APGE because:

1. AGTP-LOG already defines a transparency log aligned with RFC 9162 and RFC 9943 — the same infrastructure APGE uses.
2. AGTP defines header-based governance that takes precedence over payload fields — the same principle APGE follows.
3. AGTP already has "Trust Tier" assignments that map to APGE governance tiers.

**Action:** Request a side meeting with C. Hood to discuss AGTP+APGE composition. If AGTP-LOG and APGE can share a common transparency log format, both drafts are strengthened.

### 3.5 Risk Assessment

- **Risk:** The WG charter may explicitly exclude governance as out-of-scope.
- **Mitigation:** Frame APGE as "confirmation evidence" (which is in-scope) rather than "governance" (which may sound too broad). The difference is framing, not substance.
- **Risk:** The room may view APGE as yet another competing receipt format rather than a unifying layer.
- **Mitigation:** Emphasize that APGE does not replace DRP/PoB/ACTA — it provides a drift-aware, multi-jurisdictional envelope that can carry their receipts as sub-types.

---

## 4. Cross-BoF Coordination Plan

### 4.1 Day-by-Day Schedule

| Day | Event | APGE Action |
|---|---|---|
| **Sun 7/19** | New Participant Program, Quick Connections | Attend; meet BoF chairs |
| **Mon 7/20** | PTTH BoF, Dispatch session | Observe dispatch session; introduce APGE to ART AD |
| **Tue 7/21** | **DAWN BoF (14:00-16:00)** | **Primary DAWN intervention** |
| **Tue 7/21** | CURRENT BoF (16:30-18:00) | Rest; prepare DMSC materials |
| **Wed 7/22** | **DMSC BoF (09:00-11:00)** | **Primary DMSC intervention** |
| **Wed 7/22** | Afternoon | Side meetings with MACP authors, AGTP author |
| **Thu 7/23** | **agentproto BoF (09:00-11:00)** | **Primary agentproto intervention** |
| **Thu 7/23** | Afternoon | Follow-up with interested parties |

### 4.2 Mailing List Engagement Plan

| List | Action | Timing |
|---|---|---|
| dawn@ietf.org | Post governance-receipt binding proposal | Before 7/18 |
| dmsc@ietf.org | Post APGE+MACP AGW integration proposal | Before 7/18 |
| agentproto@ietf.org | Post APGE as "confirmation evidence" extension | Before 7/18 |
| ietf@ietf.org (if appropriate) | Announce APGE I-D availability | After I-D is published |

### 4.3 Pre-Meeting Actions (3 days before)

- [ ] **Publish I-D**: Submit draft-bdescore-apge-governance-extension-00 to IETF Datatracker (requires IETF Datatracker account + IETF Trust BCP 78/79 compliance)
- [ ] **Subscribe to mailing lists**: dawn, dmsc, agentproto (via https://www.ietf.org/participate/lists/)
- [ ] **Register for IETF 126**: https://registration.ietf.org/126/ (free remote option available per RFC 9501)
- [ ] **Post introductory messages**: One per mailing list, introducing APGE and its relevance
- [ ] **Request side meetings**: With MACP authors (China Telecom/Huawei), AGTP author (Hood)
- [ ] **Prepare slides**: 3-slide deck for each BoF (problem, solution, ask)
- [ ] **Test Meetecho**: Remote participants should test at https://meetecho-meetings.ietf.org/ietf126/?group=testing

---

## 5. Competitive Landscape Analysis

### 5.1 Existing Receipt/Governance I-Ds and APGE Differentiation

| Draft | Focus | Protocol Scope | Drift-Aware | Multi-Jurisdiction | MCP Extension |
|---|---|---|---|---|---|
| DRP [draft-nelson] | User-to-operator delegation | Protocol-agnostic | No | No | No |
| PoB [draft-dembowski] | Behavioral audit | Protocol-agnostic | No | No | No |
| ACTA [draft-farley] | Access control receipts | MCP-specific | No | No | N/A (MCP-native) |
| ASQAV [draft-marques] | EU AI Act compliance profile | MCP-specific | No | EU only | N/A |
| AIGA [draft-aylward] | Full governance architecture | Standalone protocol | Partial (TEE) | No | No |
| AGTP-LOG [draft-hood] | Transparency log | AGTP-specific | No | No | No |
| **APGE (ours)** | **Compliance governance extension** | **Any AGMP** | **Yes** | **EU + China** | **Yes** |

### 5.2 APGE's Unique Value

1. **Drift-aware governance** — No other I-D captures model-state commitments and detects post-authorization drift. This is a genuine innovation.

2. **Multi-jurisdictional compliance** — Both EU AI Act and China's regulation are binding. APGE is the only draft that addresses both simultaneously.

3. **Protocol-agnostic extension** — APGE does not compete with MCP, A2A, or AGTP. It extends all of them. This makes it the safest bet for WG adoption.

4. **MCP Extension framework integration** — The 2026-07-28 MCP spec creates a formal extensions framework. APGE is designed to be a first-class citizen in this framework (io.bdescore/apge).

5. **ERC-8226 off-chain companion** — APGE serves as the off-chain evidence layer for ERC-8226's on-chain principal eligibility, creating a bridge between IETF and Ethereum standards.

---

## 6. Regulatory Urgency Calendar

| Date | Event | APGE Implication |
|---|---|---|
| **2026-07-15** | China "Intelligent Agent Governance Implementation Opinion" enters force | APGE's cn-agent-governance profile is immediately relevant |
| **2026-07-18-24** | IETF 126 Vienna | Present APGE at three BoFs |
| **2026-07-28** | MCP 2026-07-28 specification final release | APGE's io.bdescore/apge extension becomes deployable |
| **2026-08-02** | EU AI Act Art. 50 enforcement begins | APGE's eu-ai-act-art50 profile becomes mandatory |
| **2026-Q3** | Expected agentproto WG charter (if BoF succeeds) | APGE aims for referenced extension status |
| **2026-Q4** | Expected DAWN WG formation (if BoF succeeds) | APGE aims for governance-receipt binding in discovery |

---

## 7. Remote Participation Information

Per [RFC 9501](https://www.ietf.org/rfc/rfc9501.txt), there must be an option for free remote participation in any IETF meeting.

- **Registration**: https://registration.ietf.org/126/
- **Remote participation system**: Meetecho
- **Test sessions**: Held 6-7 July 2026; test URL: https://meetecho-meetings.ietf.org/ietf126/?group=testing
- **IETF Datatracker account required**: https://datatracker.ietf.org/accounts/create/
- **Mailing list subscription**: https://www.ietf.org/participate/lists/ (Postorius interface)
- **Student registration**: $150 (covers full week)
- **Hackathon**: Free, separate registration at https://wiki.ietf.org/meeting/126/hackathon
- **Meeting agenda**: https://datatracker.ietf.org/meeting/126/agenda

### Key Mailing Lists to Subscribe

| List | Purpose | Archive |
|---|---|---|
| dawn@ietf.org | DAWN BoF discussion | IETF Mail Archive |
| dmsc@ietf.org | DMSC BoF discussion | IETF Mail Archive |
| agentproto@ietf.org | agentproto BoF discussion | IETF Mail Archive |
| ietf@ietf.org | General IETF discussion | IETF Mail Archive |
| i-d-announce@ietf.org | Internet-Draft announcements | IETF Mail Archive |

---

## 8. Success Metrics

| Outcome | Target | Measurement |
|---|---|---|
| Awareness | ≥5 key participants aware of APGE after IETF 126 | Follow-up email responses |
| Mailing list engagement | ≥2 substantive replies to APGE posts on each list | List archive count |
| Co-author interest | ≥1 draft author expresses interest in APGE integration | Direct communication |
| Side meeting | ≥1 side meeting with MACP or AGTP authors | Meeting held |
| I-D submission | draft-bdescore-apge-governance-extension-00 published on Datatracker | Datatracker status |
| Charter influence | Governance/confirmation evidence mentioned in agentproto charter discussion | BoF minutes |
