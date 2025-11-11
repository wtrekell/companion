# Accessibility Audit: [Product/Feature Name]

## Audit Information
**Product/Feature:** [Name]
**URL/Version:** [URL or version number]
**Audit Date:** [Date]
**Auditor:** [Name]
**Target WCAG Level:** [A / AA / AAA]
**WCAG Version:** [2.1 / 2.2]

---

## Executive Summary
[Brief overview of audit scope, overall compliance status, and critical findings]

**Overall Compliance:** [Estimated percentage or status]
**Critical Issues Found:** [Number]
**High Priority Issues:** [Number]
**Medium Priority Issues:** [Number]
**Low Priority Issues:** [Number]

---

## Automated Testing

### Tools Used
- [ ] [Tool 1 - e.g., Axe DevTools]
- [ ] [Tool 2 - e.g., WAVE]
- [ ] [Tool 3 - e.g., Lighthouse]

### Automated Test Results
| Tool | Score | Issues Found | Notes |
|------|-------|--------------|-------|
| [Tool name] | [Score] | [Number] | [Key findings] |

---

## Manual Testing Checklist

### 1. Perceivable

#### 1.1 Text Alternatives
- [ ] All images have appropriate alt text (1.1.1 - A)
- [ ] Decorative images have empty alt attributes
- [ ] Complex images have detailed descriptions
- [ ] Form inputs have associated labels

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 1.2 Time-based Media
- [ ] Pre-recorded audio has transcripts (1.2.1 - A)
- [ ] Pre-recorded video has captions (1.2.2 - A)
- [ ] Pre-recorded video has audio description or transcript (1.2.3 - A)
- [ ] Live audio has captions (1.2.4 - AA)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 1.3 Adaptable
- [ ] Content structure uses semantic HTML (1.3.1 - A)
- [ ] Reading order is logical and meaningful (1.3.2 - A)
- [ ] Instructions don't rely solely on sensory characteristics (1.3.3 - A)
- [ ] Orientation is not restricted (1.3.4 - AA)
- [ ] Input purpose is identified (1.3.5 - AA)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 1.4 Distinguishable
- [ ] Color is not the only means of conveying information (1.4.1 - A)
- [ ] Audio control available for auto-playing audio (1.4.2 - A)
- [ ] Text has 4.5:1 contrast ratio (normal text) (1.4.3 - AA)
- [ ] Text has 3:1 contrast ratio (large text) (1.4.3 - AA)
- [ ] Text can be resized to 200% without loss of functionality (1.4.4 - AA)
- [ ] Images of text are avoided (1.4.5 - AA)
- [ ] Text has 7:1 contrast ratio (normal text) (1.4.6 - AAA)
- [ ] Text has 4.5:1 contrast ratio (large text) (1.4.6 - AAA)
- [ ] Focus indicators have 3:1 contrast ratio (1.4.11 - AA)
- [ ] Text spacing can be adjusted without loss of content (1.4.12 - AA)

**Color Contrast Issues:**
| Element | Foreground | Background | Ratio | Required | Pass/Fail |
|---------|------------|-----------|-------|----------|-----------|
| [Element] | [Color] | [Color] | [Ratio] | [Required] | [Status] |

**Other Issues Found:**
- [Issue description - Location - WCAG criterion]

---

### 2. Operable

#### 2.1 Keyboard Accessible
- [ ] All functionality available via keyboard (2.1.1 - A)
- [ ] No keyboard traps (2.1.2 - A)
- [ ] All keyboard shortcuts are documented (2.1.4 - A)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 2.2 Enough Time
- [ ] Time limits can be adjusted/extended (2.2.1 - A)
- [ ] Moving/auto-updating content can be paused (2.2.2 - A)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 2.3 Seizures and Physical Reactions
- [ ] No content flashes more than 3 times per second (2.3.1 - A)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 2.4 Navigable
- [ ] Skip navigation links provided (2.4.1 - A)
- [ ] Page titles are descriptive (2.4.2 - A)
- [ ] Focus order is logical (2.4.3 - A)
- [ ] Link purpose is clear from text or context (2.4.4 - A)
- [ ] Multiple ways to find pages (2.4.5 - AA)
- [ ] Headings and labels are descriptive (2.4.6 - AA)
- [ ] Focus indicator is visible (2.4.7 - AA)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 2.5 Input Modalities
- [ ] Pointer gestures have keyboard/single-pointer alternatives (2.5.1 - A)
- [ ] Pointer cancellation is possible (2.5.2 - A)
- [ ] Labels match accessible names (2.5.3 - A)
- [ ] Motion actuation has alternatives (2.5.4 - A)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

### 3. Understandable

#### 3.1 Readable
- [ ] Page language is identified (3.1.1 - A)
- [ ] Language changes are identified (3.1.2 - AA)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 3.2 Predictable
- [ ] Focus doesn't trigger unexpected context changes (3.2.1 - A)
- [ ] Input doesn't trigger unexpected context changes (3.2.2 - A)
- [ ] Navigation is consistent (3.2.3 - AA)
- [ ] Components are consistently identified (3.2.4 - AA)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

#### 3.3 Input Assistance
- [ ] Error messages are clear and helpful (3.3.1 - A)
- [ ] Labels or instructions provided for input (3.3.2 - A)
- [ ] Error suggestions provided when possible (3.3.3 - AA)
- [ ] Error prevention for legal/financial transactions (3.3.4 - AA)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

### 4. Robust

#### 4.1 Compatible
- [ ] HTML is valid and properly nested (4.1.1 - A)
- [ ] Name, role, value available for all UI components (4.1.2 - A)
- [ ] Status messages can be programmatically determined (4.1.3 - AA)

**Issues Found:**
- [Issue description - Location - WCAG criterion]

---

## Screen Reader Testing

### Tools Used
- [ ] NVDA (Windows)
- [ ] JAWS (Windows)
- [ ] VoiceOver (macOS/iOS)
- [ ] TalkBack (Android)

### Screen Reader Test Results
| Component/Page | Screen Reader | Issues | Notes |
|---------------|---------------|---------|-------|
| [Component] | [SR name] | [Issues] | [Notes] |

---

## Priority Issues

### Critical (Fix Immediately)
1. **[Issue Title]**
   - **Location:** [Where the issue occurs]
   - **WCAG Criterion:** [Number and level]
   - **Description:** [Detailed description]
   - **Impact:** [Who is affected and how]
   - **Recommendation:** [How to fix]

### High Priority (Fix within 30 days)
1. **[Issue Title]**
   - **Location:** [Where the issue occurs]
   - **WCAG Criterion:** [Number and level]
   - **Description:** [Detailed description]
   - **Impact:** [Who is affected and how]
   - **Recommendation:** [How to fix]

### Medium Priority (Fix within 90 days)
1. **[Issue Title]**
   - **Location:** [Where the issue occurs]
   - **WCAG Criterion:** [Number and level]
   - **Description:** [Detailed description]
   - **Impact:** [Who is affected and how]
   - **Recommendation:** [How to fix]

### Low Priority (Fix when possible)
1. **[Issue Title]**
   - **Location:** [Where the issue occurs]
   - **WCAG Criterion:** [Number and level]
   - **Description:** [Detailed description]
   - **Impact:** [Who is affected and how]
   - **Recommendation:** [How to fix]

---

## Recommendations

### Immediate Actions
1. [Action 1]
2. [Action 2]
3. [Action 3]

### Process Improvements
1. [Improvement 1]
2. [Improvement 2]

### Training Needs
1. [Training need 1]
2. [Training need 2]

---

## Next Steps
- [ ] Share audit with stakeholders
- [ ] Prioritize fixes in sprint planning
- [ ] Schedule follow-up audit for [date]
- [ ] Implement automated testing in CI/CD
- [ ] Create accessibility guidelines for team

---

## Resources
- [WCAG 2.2 Guidelines](https://www.w3.org/WAI/WCAG22/quickref/)
- [Link to detailed test results]
- [Link to screenshots/recordings]
- [Link to accessibility documentation]
