# Site Data & Navigation Configuration

This directory centralizes global site configuration, primarily defining the main navigation structure for the 'Syntax & Empathy Companion' website.

## Summary

This section of the repository houses essential YAML files that power dynamic elements across the site, ensuring consistent navigation and site-wide data management. It provides a single, organized source for global configuration variables, making it easier for developers and content managers to maintain and update key structural components of the site. Visitors will find the definitions for the site's menus and other shared data elements here.

## About This Content

This directory is dedicated to defining the global data structures used throughout the 'Syntax & Empathy Companion' website. It primarily explores how the site's navigation and other shared content elements are structured and managed using Jekyll's `_data` feature. The approach leverages YAML files to create a clear, human-readable, and easily maintainable system for site-wide configuration.

Key insights include understanding the importance of centralized data for consistency across a Jekyll site and how structured data (like YAML) facilitates this. The content here is intended for site administrators, developers, and content creators who need to understand or modify the website's foundational data, particularly its navigation. It is a critical component of the site's architecture, enabling dynamic rendering of menus and other data-driven elements.

## Key Topics

-   **Site Navigation Definition**: How the primary and secondary menus of the website are structured and linked.
-   **Jekyll Data Files**: Understanding the role and usage of the `_data` directory in a Jekyll project for global variables.
-   **YAML Structure**: The syntax and best practices for defining hierarchical data in YAML format for web configuration.

## Content Structure

This directory contains:

-   **navigation.yml** - Defines the primary and secondary navigation menus for the entire 'Syntax & Empathy Companion' website, including link titles, URLs, and potentially sub-items.

## Reading Guide

To understand the site's menu structure, begin by reviewing the `navigation.yml` file. This file is directly consumed by Jekyll templates (e.g., in `_includes/`) to render the site's navigation. Familiarity with YAML syntax will be beneficial.

## Key Takeaways

-   The `_data` directory serves as the centralized hub for global site configuration in Jekyll.
-   `navigation.yml` is the single source of truth for the website's main navigation links.
-   Utilizing YAML in the `_data` directory ensures consistent and easily maintainable site-wide variables.

## Metadata

-   **Created:** 2023-10-27
-   **Last Updated:** 2023-10-27
-   **Status:** Published
-   **Content Type:** Configuration Data
-   **Reading Time:** 2 minutes
-   **Author:** Syntax & Empathy Companion Maintainers

## Related Content

-   `_includes/header.html` - This file (or similar layout components) typically consumes the data from `navigation.yml` to render the site's navigation bar.
-   Jekyll Documentation on Data Files - For a deeper understanding of how Jekyll processes and utilizes the `_data` directory.

## Citations & References

-   [Jekyll Data Files Documentation](https://jekyllrb.com/docs/datafiles/)

---

**Feedback:** For questions or proposed changes related to the site's navigation structure or other global data, please open an issue in the main repository.