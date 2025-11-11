# WCAG 2.2 Compliance Checklist

**Product/Feature:** [Name]
**Target Level:** [ ] A  [ ] AA  [ ] AAA
**Date:** [Date]
**Reviewer:** [Name]

---

## How to Use This Checklist

- Mark applicable items as you test them
- ✅ = Compliant
- ❌ = Non-compliant (document issue)
- N/A = Not applicable
- Document all non-compliant items with details

---

## Level A Criteria (Required for Basic Accessibility)

### Principle 1: Perceivable

#### 1.1 Text Alternatives
- [ ] **1.1.1 Non-text Content (A)** - All non-text content has text alternative

#### 1.2 Time-based Media
- [ ] **1.2.1 Audio-only and Video-only (Prerecorded) (A)** - Alternative provided
- [ ] **1.2.2 Captions (Prerecorded) (A)** - Captions for prerecorded video
- [ ] **1.2.3 Audio Description or Media Alternative (Prerecorded) (A)** - Description provided

#### 1.3 Adaptable
- [ ] **1.3.1 Info and Relationships (A)** - Structure can be programmatically determined
- [ ] **1.3.2 Meaningful Sequence (A)** - Correct reading sequence
- [ ] **1.3.3 Sensory Characteristics (A)** - Instructions don't rely solely on sensory characteristics

#### 1.4 Distinguishable
- [ ] **1.4.1 Use of Color (A)** - Color is not the only visual means of conveying information
- [ ] **1.4.2 Audio Control (A)** - Mechanism to pause or stop audio that plays automatically

---

### Principle 2: Operable

#### 2.1 Keyboard Accessible
- [ ] **2.1.1 Keyboard (A)** - All functionality available from keyboard
- [ ] **2.1.2 No Keyboard Trap (A)** - Keyboard focus can be moved away from component
- [ ] **2.1.4 Character Key Shortcuts (A)** - Can be turned off, remapped, or only active on focus

#### 2.2 Enough Time
- [ ] **2.2.1 Timing Adjustable (A)** - Time limits can be turned off, adjusted, or extended
- [ ] **2.2.2 Pause, Stop, Hide (A)** - Moving, blinking, scrolling content can be paused

#### 2.3 Seizures and Physical Reactions
- [ ] **2.3.1 Three Flashes or Below Threshold (A)** - No content flashes more than 3 times per second

#### 2.4 Navigable
- [ ] **2.4.1 Bypass Blocks (A)** - Mechanism to skip repeated blocks of content
- [ ] **2.4.2 Page Titled (A)** - Web pages have descriptive titles
- [ ] **2.4.3 Focus Order (A)** - Focus order preserves meaning and operability
- [ ] **2.4.4 Link Purpose (In Context) (A)** - Purpose of link can be determined from link text or context

#### 2.5 Input Modalities
- [ ] **2.5.1 Pointer Gestures (A)** - Multipoint or path-based gestures have single-pointer alternative
- [ ] **2.5.2 Pointer Cancellation (A)** - Down-event doesn't execute function
- [ ] **2.5.3 Label in Name (A)** - Accessible name contains visible label text
- [ ] **2.5.4 Motion Actuation (A)** - Functionality triggered by device motion has UI alternative

---

### Principle 3: Understandable

#### 3.1 Readable
- [ ] **3.1.1 Language of Page (A)** - Default language can be programmatically determined

#### 3.2 Predictable
- [ ] **3.2.1 On Focus (A)** - Focus doesn't initiate change of context
- [ ] **3.2.2 On Input (A)** - Changing setting doesn't automatically cause change of context
- [ ] **3.2.6 Consistent Help (A)** - Help mechanisms are in consistent order (WCAG 2.2)

#### 3.3 Input Assistance
- [ ] **3.3.1 Error Identification (A)** - Errors are identified and described to user
- [ ] **3.3.2 Labels or Instructions (A)** - Labels or instructions provided when input required
- [ ] **3.3.7 Redundant Entry (A)** - Information previously entered is auto-populated or available to select (WCAG 2.2)

---

### Principle 4: Robust

#### 4.1 Compatible
- [ ] **4.1.2 Name, Role, Value (A)** - Name and role can be programmatically determined
- [ ] **4.1.3 Status Messages (AA)** - Status messages can be programmatically determined

---

## Level AA Criteria (Required for Meaningful Accessibility)

### Principle 1: Perceivable

#### 1.2 Time-based Media
- [ ] **1.2.4 Captions (Live) (AA)** - Captions for live audio content
- [ ] **1.2.5 Audio Description (Prerecorded) (AA)** - Audio description for prerecorded video

#### 1.3 Adaptable
- [ ] **1.3.4 Orientation (AA)** - Content doesn't restrict to single display orientation
- [ ] **1.3.5 Identify Input Purpose (AA)** - Input purpose can be programmatically determined

#### 1.4 Distinguishable
- [ ] **1.4.3 Contrast (Minimum) (AA)** - 4.5:1 for text, 3:1 for large text
- [ ] **1.4.4 Resize Text (AA)** - Text can be resized to 200% without loss of functionality
- [ ] **1.4.5 Images of Text (AA)** - Text used instead of images of text
- [ ] **1.4.10 Reflow (AA)** - No 2D scrolling at 320px width
- [ ] **1.4.11 Non-text Contrast (AA)** - 3:1 contrast for UI components and graphics
- [ ] **1.4.12 Text Spacing (AA)** - No loss of content with increased text spacing
- [ ] **1.4.13 Content on Hover or Focus (AA)** - Hoverable, dismissable, persistent

---

### Principle 2: Operable

#### 2.4 Navigable
- [ ] **2.4.5 Multiple Ways (AA)** - Multiple ways to locate pages
- [ ] **2.4.6 Headings and Labels (AA)** - Headings and labels describe topic or purpose
- [ ] **2.4.7 Focus Visible (AA)** - Keyboard focus indicator is visible
- [ ] **2.4.11 Focus Not Obscured (Minimum) (AA)** - Focused item is at least partially visible (WCAG 2.2)

#### 2.5 Input Modalities
- [ ] **2.5.7 Dragging Movements (AA)** - Single pointer alternative for dragging (WCAG 2.2)
- [ ] **2.5.8 Target Size (Minimum) (AA)** - Targets are at least 24x24 CSS pixels (WCAG 2.2)

---

### Principle 3: Understandable

#### 3.1 Readable
- [ ] **3.1.2 Language of Parts (AA)** - Language of passages can be programmatically determined

#### 3.2 Predictable
- [ ] **3.2.3 Consistent Navigation (AA)** - Navigation mechanisms are consistent
- [ ] **3.2.4 Consistent Identification (AA)** - Components with same functionality are identified consistently

#### 3.3 Input Assistance
- [ ] **3.3.3 Error Suggestion (AA)** - Suggestions provided for input errors
- [ ] **3.3.4 Error Prevention (Legal, Financial, Data) (AA)** - Submissions can be reversed, checked, or confirmed
- [ ] **3.3.8 Accessible Authentication (Minimum) (AA)** - No cognitive function test unless alternative provided (WCAG 2.2)

---

## Level AAA Criteria (Enhanced Accessibility - Optional)

### Principle 1: Perceivable

#### 1.2 Time-based Media
- [ ] **1.2.6 Sign Language (Prerecorded) (AAA)** - Sign language interpretation provided
- [ ] **1.2.7 Extended Audio Description (Prerecorded) (AAA)** - Extended audio description when pauses insufficient
- [ ] **1.2.8 Media Alternative (Prerecorded) (AAA)** - Alternative for time-based media
- [ ] **1.2.9 Audio-only (Live) (AAA)** - Alternative for live audio

#### 1.3 Adaptable
- [ ] **1.3.6 Identify Purpose (AAA)** - Purpose of UI components can be programmatically determined

#### 1.4 Distinguishable
- [ ] **1.4.6 Contrast (Enhanced) (AAA)** - 7:1 for text, 4.5:1 for large text
- [ ] **1.4.7 Low or No Background Audio (AAA)** - Audio is clear or can be turned off
- [ ] **1.4.8 Visual Presentation (AAA)** - Presentation can be customized
- [ ] **1.4.9 Images of Text (No Exception) (AAA)** - Images of text only for decoration

---

### Principle 2: Operable

#### 2.1 Keyboard Accessible
- [ ] **2.1.3 Keyboard (No Exception) (AAA)** - All functionality available from keyboard

#### 2.2 Enough Time
- [ ] **2.2.3 No Timing (AAA)** - No time limits
- [ ] **2.2.4 Interruptions (AAA)** - Interruptions can be postponed or suppressed
- [ ] **2.2.5 Re-authenticating (AAA)** - User can continue after re-authentication
- [ ] **2.2.6 Timeouts (AAA)** - Users warned of timeouts (WCAG 2.2)

#### 2.3 Seizures and Physical Reactions
- [ ] **2.3.2 Three Flashes (AAA)** - No content flashes more than 3 times per second
- [ ] **2.3.3 Animation from Interactions (AAA)** - Motion animation can be disabled

#### 2.4 Navigable
- [ ] **2.4.8 Location (AAA)** - Information about location within set of pages
- [ ] **2.4.9 Link Purpose (Link Only) (AAA)** - Link purpose from link text alone
- [ ] **2.4.10 Section Headings (AAA)** - Headings used to organize content
- [ ] **2.4.12 Focus Not Obscured (Enhanced) (AAA)** - Focused item is fully visible (WCAG 2.2)
- [ ] **2.4.13 Focus Appearance (AAA)** - Focus indicator meets size and contrast requirements (WCAG 2.2)

#### 2.5 Input Modalities
- [ ] **2.5.5 Target Size (Enhanced) (AAA)** - Targets are at least 44x44 CSS pixels
- [ ] **2.5.6 Concurrent Input Mechanisms (AAA)** - Doesn't restrict input modalities

---

### Principle 3: Understandable

#### 3.1 Readable
- [ ] **3.1.3 Unusual Words (AAA)** - Mechanism for identifying unusual words
- [ ] **3.1.4 Abbreviations (AAA)** - Mechanism for identifying abbreviations
- [ ] **3.1.5 Reading Level (AAA)** - Lower secondary education level or alternative provided
- [ ] **3.1.6 Pronunciation (AAA)** - Mechanism for pronunciation

#### 3.2 Predictable
- [ ] **3.2.5 Change on Request (AAA)** - Changes of context initiated only by user request

#### 3.3 Input Assistance
- [ ] **3.3.5 Help (AAA)** - Context-sensitive help available
- [ ] **3.3.6 Error Prevention (All) (AAA)** - All submissions can be reversed, checked, or confirmed
- [ ] **3.3.9 Accessible Authentication (Enhanced) (AAA)** - No cognitive function test (WCAG 2.2)

---

## Summary

### Compliance Status
- **Level A:** [X of Y] criteria met ([Percentage]%)
- **Level AA:** [X of Y] criteria met ([Percentage]%)
- **Level AAA:** [X of Y] criteria met ([Percentage]%)

### Overall Assessment
**Target Compliance Level:** [A/AA/AAA]
**Current Status:** [Compliant / Partially Compliant / Non-Compliant]

### Critical Gaps
1. [Gap 1]
2. [Gap 2]
3. [Gap 3]

### Next Steps
- [ ] [Action item 1]
- [ ] [Action item 2]
- [ ] [Action item 3]

---

## References
- [WCAG 2.2 Guidelines](https://www.w3.org/WAI/WCAG22/quickref/)
- [Understanding WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/)
- [How to Meet WCAG (Quick Reference)](https://www.w3.org/WAI/WCAG22/quickref/)
