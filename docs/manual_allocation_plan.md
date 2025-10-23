# Manual Allocation Page - Implementation Plan

## Overview
Create a new Manual Allocation page (`pages/7_🖱️_Alocação_Manual.py`) with a two-column layout: **Queue of Pending Demands** (left) + **Smart Allocation Assistant** (right). This leverages the existing atomic time block system, rules engine, and professor preferences to provide one-click allocation with intelligent room suggestions.

## Confirmed Requirements
- Two-column layout with demand queue + allocation assistant
- Prioritize suggestions: hard rules first → soft preferences → availability
- Include both semester and ad-hoc reservations in conflict detection
- Individual allocations only (keep it simple)
- Always allow manual room selection with warnings (fully manual control)

## Implementation Order

1. Create Core Suggestion Algorithm
2. Build Allocation Service
3. Create UI Components
4. Implement Main Page
5. Add Navigation Links
6. Test End-to-End Flow
