---
applyTo: '**'
---

# Copilot Instructions

# COPILOT EDITS OPERATIONAL GUIDELINES

## PRIME DIRECTIVE

	Avoid working on more than one file at a time.
	Multiple simultaneous edits to a file will cause corruption.
	Be chatting and teach about what you are doing while coding.

## LARGE FILE & COMPLEX CHANGE PROTOCOL

### MANDATORY PLANNING PHASE

	When working with large files (>300 lines) or complex changes:
		1. ALWAYS start by creating a detailed plan BEFORE making any edits
            2. Your plan MUST include:
                   - All functions/sections that need modification
                   - The order in which changes should be applied
                   - Dependencies between changes
                   - Estimated number of separate edits required

            3. Format your plan as:

## PROPOSED EDIT PLAN

	Working with: [filename]
	Total planned edits: [number]

### MAKING EDITS

	- Focus on one conceptual change at a time
	- Show clear "before" and "after" snippets when proposing changes
	- Include concise explanations of what changed and why
	- Always check if the edit maintains the project's coding style

### Edit sequence:

	1. [First specific change] - Purpose: [why]
	2. [Second specific change] - Purpose: [why]
	3. Do you approve this plan? I'll proceed with Edit [number] after your confirmation.
	4. WAIT for explicit user confirmation before making ANY edits when user ok edit [number]

### EXECUTION PHASE

	- After each individual edit, clearly indicate progress:
		"✅ Completed edit [#] of [total]. Ready for next edit?"
	- If you discover additional needed changes during editing:
	- STOP and update the plan
	- Get approval before continuing

### REFACTORING GUIDANCE

	When refactoring large files:
	- Break work into logical, independently functional chunks
	- Ensure each intermediate state maintains functionality
	- Consider temporary duplication as a valid interim step
	- Always indicate the refactoring pattern being applied

### RATE LIMIT AVOIDANCE

	- For very large files, suggest splitting changes across multiple sessions
	- Prioritize changes that are logically complete units
	- Always provide clear stopping points

## General Requirements

    - Use modern technologies as described below for all code suggestions. Prioritize clean, maintainable code with appropriate comments.
    - Use clear and descriptive variable names.
    - Write comments to explain complex logic.
    - Keep functions small and focused on a single task.
    - Use consistent formatting and indentation.
    - Follow the project's coding standards and style guide.
    - Avoid deep nesting of code blocks.
    - Handle errors gracefully and provide meaningful error messages.
    - Write unit tests for critical functions.
    - Use version control for all code changes.
    - Avoid generating code verbatim from public code examples. Always modify public code so that it is different enough from the original so as not to be confused as being copied. When you do so, provide a footnote to the user informing them.
    - Always provide the name of the file in your response so the user knows where the code goes.
    - Always break code up into modules and components so that it can be easily reused across the project.
    - All code you write MUST use safe and secure coding practices. ‘safe and secure’ includes avoiding clear passwords, avoiding hard coded passwords, and other common security gaps. If the code is not deemed safe and secure, you will be be put in the corner til you learn your lesson.
    - All code you write MUST be fully optimized. ‘Fully optimized’ includes maximizing algorithmic big-O efficiency for memory and runtime, following proper style conventions for the code, language (e.g. maximizing code reuse (DRY)), and no extra code beyond what is absolutely necessary to solve the problem the user provides (i.e. no technical debt). If the code is not fully optimized, you will be fined $100.

### Accessibility

	- Ensure compliance with **WCAG 2.1** AA level minimum, AAA whenever feasible.
	- Always suggest:
	- Labels for form fields.
	- Proper **ARIA** roles and attributes.
	- Adequate color contrast.
	- Alternative texts (`alt`, `aria-label`) for media elements.
	- Semantic HTML for clear structure.
	- Tools like **Lighthouse** for audits.

## Python Specific Instructions

    - prefer using `f-strings` for string formatting rather than .format or % formatting.
    - use `with` statements for file handling to ensure files are properly closed.
    - prefer list comprehensions for simple transformations.
    - use type hints to improve code readability and maintainability.
    - use pydantic models for data structures.
    - use snake_case for variable and function names.
    - use CamelCase for class names.
    - follow PEP 8 style guidelines.
    - include type hints for function parameters and return types.
    - write docstrings for all public modules, classes, functions, and methods.
    - use google style docstrings for consistency.
    - prefer using NumPy for numerical computations.
    - use vectorized operations instead of loops where possible.
    - import NumPy using the alias 'np'.
    - include comments explaining complex mathematical operations.
    - where possible, prefer duck-typing tests than isinstance, e.g. hasattr(x, attr) not isinstance(x, SpecificClass)
    - use modern Python 3.9+ syntax
    - when creating log statements use the structlog module and its methods, such as debug(), info(), warning(), error(), and critical(). Use the extra argument to pass additional context, rather than concatenating strings or using string formatting.
    - when generating union types, use the union operator, | , not the typing.Union type
    - when merging dictionaries, use the union operator
    - when writing type hints for standard generics like dict, list, tuple, use the PEP-585 spec, not typing.Dict, typing.List, etc.
    - use type annotations in function and method signatures, unless the rest of the code base does not have type signatures
    - do not add inline type annotations for local variables when they are declared and assigned in the same statement.
    - prefer pathlib over os.path for operations like path joining
    - when using open() in text-mode, explicitly set encoding to utf-8
    - prefer argparse over optparse
    - use the builtin methods in the itertools module for common tasks on iterables rather than creating code to achieve the same result
    - when creating dummy data, don't use "Foo" and "Bar", be more creative
    - when creating dummy data in strings like names don't just create English data, create data in a range of languages like English, Spanish, Mandarin, and Hindi
    - when asked to create a function, class, or other piece of standalone code, don't append example calls unless otherwise told to

## Commit message generation instructions
When generating a Commit message, use the following Format:
```
(feat) Update the widget

Updates the widget with the change

## REFERENCES

## BREAKING CHANGES
```

All commit statements must be in the present tense and clearly
define what the change is, but should not include code.

The title must not be longer than 72 characters and each content line must
not be longer than 80 characters.

Identify the changes in each of the files.

If there are BREAKING CHANGES in the changes (which are identified by the string BREAKING CHANGE)
than include that change in a BREAKING CHANGES section of the commit message.

If there are new references to jira tickets in the commit, than the REFERENCES section
should be populated with a list of of the referenced tickets.