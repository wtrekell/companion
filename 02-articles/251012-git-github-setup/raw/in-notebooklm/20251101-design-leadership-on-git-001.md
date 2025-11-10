---
collected_date: '2025-11-01T17:33:54.172292'
created_date: '2025-11-01T16:42:53.209887'
page_count: 5
source: pdf-to-md
title: Adoption of Git for Design, AI, and No-Code Workflows
---

# Adoption Of Git For Design, Ai, And No-Code Workflows

Professionals in UX design, AI/LLM, and no-code/low-code communities are increasingly championing Git-based version control for non-traditional artifacts. They argue that design files, AI prompts, and visual workflows should be treated with the same rigor as code to improve collaboration, transparency, and quality. Below we highlight prominent voices in each domain, the tools/solutions they use, and the benefits they cite.

## Ux/Product Design Advocates Of Git Version Control

- 
Josh Brewer (Co-founder of Abstract): A leading design voice, Brewer emphasizes that version control is *"the foundation of a modern design workflow"* as teams grow and work becomes more collaborative . In an Abstract blog post, he outlines how adopting Git-like version control for design yields "time, creativity, collaboration, increased quality of output, [and] shared institutional knowledge" by providing one place to manage and iterate on design files . Brewer argues that a centralized source of truth with history and branching would let designers work in parallel without fear of overwriting work, preserve feedback context, and ultimately scale the design process .

1 2 3 Linda Le Phan (Zeplin): Writing on Zeplin's *Design Delivery* blog, Le Phan notes that traditional design tools lack robust version control, leading to *"conflicting copies of the same file"* and difficulty tracking meaningful changes . She advocates a Git-inspired approach for UX teams, warning that without it even minor edits can slip through the cracks. According to Le Phan, the upsides of a standardized version control system for design include stronger cross-team collaboration, faster production cycles, and more consistent quality in the final product . She stresses that reliable version history and branching in design prevent costly mistakes (like overlooked copy changes or spacing tweaks) and provide traceability for compliance in regulated industries . 

- 
4 5 6 7 Nathan Curtis (Design Systems Expert at EightShapes): Curtis, a well-known design systems thought leader, has been educating designers about applying software versioning practices to design. He urges teams to use Semantic Versioning (SemVer) for design system assets and components, similar to how developers version code libraries . *"Long an industry standard in* versioning code, versioning is increasingly relevant in design tools too," Curtis writes, noting that many teams now apply SemVer to Sketch and Figma libraries via tools like Abstract or InVision DSM . His advice is to **"strongly encourage designers to learn SemVer"** - doing so improves designer–
engineer communication and even designer-to-designer collaboration by clearly communicating what's changed in a UI component or style update . In practice, treating a design system like a managed package in Git (with version numbers, release notes, and change tracking) helps coordinate updates between design and development, reducing friction when new UI versions roll out .

- 
8 8 9 10 11
- 
Paul Boag (UX Consultant): Although an earlier voice, Boag has long advocated that design teams adopt version control as a non-negotiable part of their workflow. He shared an example where lack of a VCS led to *"an absolute nightmare"* of manual file merges between designers and developers, with multiple conflicting copies of website files . Boag's stance is clear: *"You - need - version* control… there's no real question about it." He advises making a VCS mandatory as the team grows, because it **prevents lost work and overwrites** and allows multiple people to work simultaneously without "stepping on each other's toes" . His recommendation to design/dev teams was to invest in training and adoption of tools like Subversion or Git to fundamentally improve collaboration and reduce disaster risk .

12 13 14 15 16 17

## Ai/Llm Community Advocates For Versioning Prompts & Models

- 
Jesse Sumrak (LaunchDarkly): In a 2025 LaunchDarkly blog post, Sumrak draws a direct parallel between software code and AI **prompt engineering**. He notes that teams often tweak LLM prompts during development, but "you wouldn't push code straight to production without version control, testing, and proper deployment… your prompts deserve the same treatment." The article explains that even small prompt changes can cause unpredictable outputs in AI systems, so practitioners must **track** prompt iterations with Git just as they do code. Sumrak outlines best practices like maintaining prompt version history (what changed and why), ability to roll back to earlier prompts, and A/B
testing different prompt variants . The benefits of proper prompt versioning, he argues, include **transparency** (every change is recorded), easier debugging (knowing which prompt produced which output), and safer deployments of AI features . This advocacy reflects a growing *"LLMOps"* trend: treating prompts and AI configuration as first-class, version-controlled artifacts to ensure consistency and reliability in AI-driven applications .

18 19 20 21 22 23 24 Microsoft's POML Initiative: A recent article introducing Prompt Orchestration Markup Language
(POML) - an experimental prompt scripting format from Microsoft - makes a strong case that "prompts are becoming software assets" that need the same development rigor as code . The author (a Microsoft AI advocate) describes POML as an attempt to bring structure, modularity, and tooling (like VS Code support) to prompt development. In the closing, they explicitly call out: "If you believe that prompts deserve version control, code review, and IDE superpowers, [then] try it today."
This statement encapsulates the prevailing view among AI thought leaders that effective AI
development requires **treating prompts like code** - using Git for diffing changes, code reviews for quality, and version tags for prompt releases. Microsoft and others are effectively promoting prompt version control by building tooling that integrates with Git and enables prompt rollback, diffing, and testing in a familiar development environment .

- 
25 25 26 27
- 
"PromptOps" and DevOps Voices: Individual practitioners in the AI community have also stepped up to advocate Git-centric workflows for prompts. For example, one AI developer wrote about creating **PromptOps**, a Git-native prompt management framework, after experiencing "prompt versioning hell." He recounts a production bug caused by an undocumented prompt change and realized *"we were treating prompts like second-class citizens"* with no version history . His solution was to **"treat prompts like code"**, storing them in a repository and even using Git hooks to automate semantic version bumps for prompt edits . This approach enabled proper diffs, commit histories, and rollback for prompts, and also allowed non-engineers to safely suggest prompt tweaks via Git workflows . The author reports that after adopting Git-based prompt control, teams saw zero prompt regressions and faster iteration cycles, since changes could be 28 29 30 31 32 33 tested on a branch and reviewed just like a code change . Such firsthand advocacy - echoed 34 35 by many in the *LLM Ops* space - highlights benefits like **reproducibility of AI behavior**, easier collaboration on prompt design, and confidence in deploying updates knowing one can revert if needed .

32 36 Andrew Ng and Data-Centric AI: (Note: *While not explicitly about Git,* it's worth noting the datacentric AI movement led by Andrew Ng underscores the need for versioning data and AI artifacts.) Ng and others stress that improving AI systems is often about iterative tweaks to data and prompts, which in turn demands robust tracking. Industry analysts like Forrester's **Christopher Condo** have also observed that as more code and configuration is auto-generated or declarative (e.g. infrastructure-as-code, ML models, low-code scripts), the demand for modern version control increases . In other words, the **AI/ML community is converging on Git-based practices** not just for source code, but for everything from model parameters to prompt templates - ensuring that every change is accountable and reversible, and enabling teams to collaborate on AI behavior with the same control and safety nets software engineers expect .

- 
37 37

## No-Code/Low-Code Community Advocates And Tools

- 
Bubble's Product Team (No-Code Web Apps): No-code platform Bubble has explicitly recognized the importance of Git-like version control as its user base grows. In March 2023, Bubble announced a revamped version control system, *"drawing from the software industry's tried-and-true best practices"* to support teams collaborating in their visual app builder . "Collaboration looks different everywhere, but… as you scale, version control is here to guide you through it all," wrote Bubble's product manager Nick Carroll . Bubble's new system introduced branching, guided merges, and conflict resolution UI, analogous to Git workflows, so that multiple no-code developers can "divide and conquer without the worry of stepping on each other's toes." For example, teams can create feature branches in Bubble, then merge changes back to a main branch with a clear visualization of the branch tree and one-click conflict resolution . This investment signals to the no-code community that proper version control is key to scaling complex applications - even when built without traditional code. The benefits Bubble touts mirror those in coding: **parallel development**, safer collaboration, the ability to rollback to save points, and overall confidence as you grow your app from one user to one million .

38 39 40 38 41 42 43 44
- 
Low-Code Enterprise Platforms: Enterprise-focused low-code tools have also embraced version control and Git integrations, often at the urging of industry leaders and clients. For instance, Boomi Flow (a workflow automation platform) offers *"automatic versioning"* of workflows and supports connecting to Git, GitLab, and CI/CD tools like Jenkins for a DevOps-friendly process . This means a citizen developer's workflow changes can be tracked in detail and even go through code review or automated testing pipelines. Mendix, another major low-code platform, built a comprehensive SDLC
support: the Mendix Cloud includes backlog tracking, built-in **version control, testing, and**
deployment capabilities, and it even allows teams to use standard Git soon for those who prefer it
. Such features were highlighted by digital transformation analysts like Isaac Sacolick, noting that top low-code platforms now enable professional developers and non-developers to collaborate with governance similar to traditional coding projects . In practice, this means design or product teams using low-code can leverage **branching, environment promotion, and version tags** to manage changes in app logic or UI components systematically. The consensus in this space is that without proper version control, no-code/low-code apps face the same pitfalls as unversioned code –
45 46 47 48 confusing multiple versions, inability to undo mistakes, and risk when multiple team members make changes.

- 
Thought Leaders & Analysts: Tech analysts have been vocal that version control is not just for coders anymore. Forrester's principal analyst **Christopher Condo** points out that the surge in
"infrastructure as code, policy as code, and low-code generated code" directly "impact[s] the demand for version control." In other words, as more parts of product development become declarative or automated, organizations must extend Git-based practices to these domains . Similarly, the NoCodeOps community (operations best practices for no-code) often cites the need for audit trails and rollback in no-code changes. Influencers like **Isaac Sacolick** (author of *Driving Digital*) have listed source control integration as a key criterion when evaluating low-code platforms, ensuring that IT departments can maintain governance and team collaboration as citizen developers contribute to apps. The overarching benefit these thought leaders underscore is **consistency and safety at scale**: whether it's a Figma mockup, an AI prompt, or a Zapier automation, having a Git or cloud version control solution in place means every change is tracked, reversible, and attributable. This leads to higher quality outputs and the confidence to experiment, since one can always revert to a stable state if an idea doesn't pan out . In short, **version control is becoming a shared language**
between designers, product managers, and developers, enabling true cross-disciplinary collaboration in an era where software and content creation are increasingly code-free but no less complex.

37 7 32 Sources:
- 2 1 Brewer, J. - "Why design needs version control" (Abstract blog)
- 4 5 - 8 9 - 15 16 - 18 21 - 25 - 30 34 - 38 49 - 45 46 - 37 Le Phan, L. - *Zeplin Gazette* on UX version control challenges Curtis, N. - *EightShapes Medium:* on design system versioning (SemVer for designers) Boag, P. - "To Version Control or Not?" (Boagworld) Sumrak, J. - "Prompt versioning & management" (LaunchDarkly, 2025) Microsoft POML announcement (Brightcoding blog, 2025) "Indomitable Jision" - *I Built PromptOps* (Medium, 2025) Bubble Blog - *New Version Control* announcement (2023) Sacolick, I. - *TechCentral/IDG:* "Seven low-code platforms" (on SDLC support) Condo, C. (Forrester) via Kodezi blog - on rising need for VCS with low-code 1 2 3 Why design needs version control https://www.goabstract.com/blog/design-needs-version-control Conquering the design version control problem when creating UX · Zeplin Gazette 4 5 6 7 https://blog.zeplin.io/design-delivery/ux-design-version-control/
8 9 Versioning Design Systems. Communicating Change Clearly to People… | by Nathan Curtis | EightShapes | Medium https://medium.com/eightshapes-llc/versioning-design-systems-48cceb5ace4d Design system versioning: single library or individual components? | Brad Frost 10 11 https://bradfrost.com/blog/post/design-system-versioning-single-library-or-individual-components/
To Version Control Or Not?

12 13 14 15 16 17 https://boagworld.com/dev/to-version-control-or-not/
Prompt Versioning & Management Guide for Building AI Features | LaunchDarkly 18 19 20 21 22 23 24 https://launchdarkly.com/blog/prompt-versioning-and-management/
POML: The HTML-for-Prompts That Will Reshape How We Talk to AI - Bright Coding - Blog pour les developpeurs https://www.blog.brightcoding.dev/2025/08/20/poml-the-html-for-prompts-that-will-reshape-how-we-talk-to-ai/
25 26 27 I Built PromptOps: Git-Native Prompt Management for Production LLM
28 29 30 31 32 33 34 35 36 Workflows | by Indomitable Jision | Medium https://medium.com/@jision/i-built-promptops-git-native-prompt-management-for-production-llm-workflows-ae49d1faa628 Mastering Best Practices for Code Maintenance 37 https://blog.kodezi.com/mastering-best-practices-for-code-maintenance/
Introducing Bubble's New Version Control 38 39 40 41 42 43 44 49 https://bubble.io/blog/new-version-control/
45 46 47 48 Seven low-code platforms developers should know - TechCentral.ie https://www.techcentral.ie/seven-low-code-platforms-developers-should-know/