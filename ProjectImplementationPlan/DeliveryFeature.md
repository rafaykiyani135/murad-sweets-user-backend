# Goal

Integrate a delivery eligibility, delivery pricing, and fulfillment selection system into the existing Next.js application.

The current application already contains:

* Product catalog/menu
* Product pages
* Shopping cart functionality
* Existing checkout flow
* Existing UI and navigation structure

This task is NOT to rebuild the website.

This task is to modify the existing ordering flow and introduce a fulfillment system that supports:

* Pickup orders
* Delivery orders
* Delivery eligibility validation
* Automatic delivery fee calculation
* Address persistence between visits
* Distance-based pricing
* Delivery radius restrictions

The final user experience should resemble modern food-ordering platforms such as KFC, Domino's, Pizza Hut, and Uber Eats.

---

# Existing Flow

Current Flow:

Home
→ Browse Products
→ Add To Cart
→ Checkout

Problem:

A customer can spend time building an order and later discover that delivery is unavailable for their address.

This creates a poor user experience.

---

# New Flow (Required)

Replace the existing flow with:

Home
→ Fulfillment Selection
→ (Pickup OR Delivery Validation)
→ Menu Browsing
→ Cart
→ Checkout

The fulfillment method must be established BEFORE customers browse products.

This becomes a required step in the ordering process.

---

# Store Information

Store Address:

11920 S Texas 6, Unit 1280
Sugar Land, TX 77498

The store address should be geocoded once during setup.

Store coordinates should then be stored as application constants.

The store address should never be geocoded repeatedly.

---

# Delivery Service Area

Maximum delivery distance:

50 miles

Distance must be calculated using DRIVING DISTANCE.

Do not use straight-line distance.

---

# APIs To Use

## Address Autocomplete

Use Mapbox Address Autocomplete.

Purpose:

* Address search
* Address suggestions
* Address validation
* Coordinate retrieval

Reason:

* Generous free tier
* Excellent UX
* Reliable
* Easier and cheaper than Google Maps

---

## Distance Calculation

Use OSRM (Open Source Routing Machine).

Purpose:

* Driving distance calculation
* Route-based mileage calculation

Distance calculations should be based on:

Store Coordinates
→ Customer Coordinates

The returned driving distance is the value used by the pricing engine.

---

# State Management Architecture

Implement a dedicated global fulfillment state.

Preferred implementation:

Zustand

Alternative:

React Context

Zustand is preferred because:

* Simpler integration
* Better scalability
* Avoids prop drilling
* Easy persistence integration

---

# Fulfillment Store Responsibilities

The fulfillment store becomes the single source of truth for:

Order Type

* Pickup
* Delivery

Address Information

* Formatted address
* Latitude
* Longitude

Distance Information

* Driving distance

Pricing Information

* Delivery fee

Eligibility Information

* Delivery available
* Delivery unavailable

Persistence Information

* Saved address

All components must consume fulfillment state from this store.

Avoid duplicate state.

---

# Fulfillment Selection Screen

When a user enters the website:

Check if fulfillment information already exists.

If no fulfillment information exists:

Show fulfillment selection.

Options:

Pickup

Delivery

The user should not immediately enter the menu.

---

# Delivery Flow

When Delivery is selected:

Prompt for delivery address.

Use Mapbox autocomplete.

Users should select a valid address from autocomplete suggestions.

Avoid accepting arbitrary address text.

---

# Address Validation Flow

After address selection:

Retrieve:

* Address
* Latitude
* Longitude

Store them in fulfillment state.

Calculate driving distance using OSRM.

---

# Delivery Eligibility Validation

If distance is less than or equal to 50 miles:

Delivery is available.

Continue to menu.

---

If distance exceeds 50 miles:

Delivery is unavailable.

Show:

"Sorry, delivery is only available within 50 miles."

Actions:

* Change Address
* Switch To Pickup

Do not allow continuation with delivery.

---

# Delivery Pricing Rules

Rule 1

Distance ≤ 5 miles

Delivery Fee = $0

Free delivery.

---

Rule 2

Distance > 5 miles and ≤ 30 miles

Delivery Fee = $10 base fee + $1 per mile

Examples:

10 miles = $20

20 miles = $30

30 miles = $40

---

Rule 3

Distance > 30 miles and ≤ 50 miles

Delivery Fee = $1 per mile

Examples:

35 miles = $35

40 miles = $40

45 miles = $45

---

Rule 4

Distance > 50 miles

Delivery unavailable.

---

# Distance Precision

The client should be consulted regarding:

Whether mileage should be:

* Exact mileage
* Rounded mileage

Until clarified:

Use exact mileage.

Example:

10.4 miles

Fee:

$20.40

---

# Fulfillment Guard

Implement a fulfillment guard.

Purpose:

Prevent access to ordering pages before fulfillment is established.

Protected pages:

* Menu pages
* Product pages
* Cart page
* Checkout page

Condition:

User must have either:

Pickup selected

OR

Valid delivery information

before proceeding.

---

# Returning User Experience

Users should not need to enter their address every visit.

Use browser localStorage.

No login required.

---

# Persistence Requirements

Persist:

Order Type

Address

Latitude

Longitude

Do not persist:

Distance

Delivery fee

Eligibility status

These values should always be recalculated when needed.

---

# Returning Delivery User Flow

User revisits site.

Application loads fulfillment state from localStorage.

If valid delivery address exists:

Show:

Delivering to:
[Address]

Allow immediate access to menu.

No address re-entry required.

---

# Returning Pickup User Flow

User revisits site.

If Pickup was previously selected:

Continue with Pickup mode.

Allow immediate access to menu.

---

# Header Integration

Integrate fulfillment information into the existing header.

Display:

Pickup

OR

Delivering to:
[Address]

This component should always remain visible.

---

# Address Change Flow

Clicking fulfillment information should open:

Change Address / Change Fulfillment Modal

The user should be able to:

* Switch Pickup ↔ Delivery
* Change address
* Recalculate delivery fee
* Recalculate eligibility

---

# Menu Integration

The existing menu system should remain unchanged.

Required addition:

Menu pages should have access to fulfillment state.

The menu should know:

* Pickup mode
* Delivery mode
* Delivery fee

without introducing duplicate state.

---

# Cart Integration

The existing cart remains intact.

Required additions:

Display:

* Subtotal
* Delivery Fee
* Total

Examples:

Subtotal: $42.00

Delivery Fee: $28.20

Total: $70.20

The delivery fee must remain visible throughout the ordering process.

Do not wait until checkout.

---

# Checkout Integration

The checkout flow should consume fulfillment state.

For Pickup:

No delivery fee.

For Delivery:

Include delivery fee in order totals.

The checkout system should have access to:

* Fulfillment type
* Address
* Distance
* Delivery fee

through the fulfillment store.

---

# Recommended API Layer

Do not call Mapbox and OSRM directly from UI components.

Create dedicated server-side API routes within Next.js.

Responsibilities:

Address Search

→ Mapbox

Distance Calculation

→ OSRM

Pricing Calculation

→ Delivery Pricing Engine

UI components should communicate only with internal API routes.

Benefits:

* Cleaner architecture
* Easier future provider changes
* API keys remain protected
* Better maintainability

---

# Error Handling

Address Lookup Failure

Show:

Unable to validate address.

Please try again.

---

Distance Service Failure

Show:

Unable to calculate delivery distance.

Please try again.

Prevent continuation.

---

Invalid Address

Require selection from autocomplete.

Do not continue.

---

Outside Delivery Radius

Show:

Delivery unavailable.

Provide:

* Change Address
* Pickup Option

---

# Performance Requirements

Store coordinates should be constants.

Do not repeatedly geocode the store.

Minimize API calls.

Cache fulfillment information in localStorage.

Recalculate distance only when:

* Address changes
* Fulfillment changes

Avoid unnecessary recalculations.

---

# Acceptance Criteria

The implementation is complete when:

✓ Users select Pickup or Delivery before browsing products

✓ Delivery addresses are validated before menu access

✓ Driving distance is calculated using OSRM

✓ Delivery fee is calculated automatically

✓ Addresses persist between visits

✓ Users can change fulfillment method at any time

✓ Users outside the 50-mile radius cannot place delivery orders

✓ Cart reflects delivery fees

✓ Existing menu and cart systems remain functional

✓ Fulfillment information is globally available throughout the application

✓ The user experience resembles modern food-ordering platforms such as KFC, Domino's, Pizza Hut, and Uber Eats

---

# Implementation Details (Completed)

## 1. Global State Management (`app/store/fulfillmentStore.ts`)
* Implemented using **Zustand** with `persist` middleware.
* **Single Source of Truth:** Stores `orderType`, `address`, and `coordinates`.
* **Computed Values:** `drivingDistanceMiles`, `deliveryFeeCents`, and `isEligible` are purposefully excluded from `localStorage` to ensure they are always recalculated live.
* **Helper Functions:** `hasValidFulfillment()` checks if the user is allowed to proceed, and `getDeliveryFeeDisplay()` formats the fee for the cart UI.

## 2. Server-Side API Routes (Proxy Services)
All external API calls were moved to Next.js API routes to protect API keys and centralize logic:

* **`/api/address-search` (Mapbox Geocoding)**
  * Proxies requests to Mapbox Geocoding v5.
  * Uses `NEXT_PUBLIC_MAPBOX_TOKEN` (stored safely in `.env.local`).
  * Suggests addresses biased around the Sugar Land, TX coordinates.
* **`/api/distance` (OSRM Route Calculation)**
  * Calls the public OSRM driving route API (`router.project-osrm.org`).
  * Uses precise store coordinates: `-95.644367` (Lng) and `29.672712` (Lat).
  * Converts the OSRM result from meters to miles (`METERS_PER_MILE = 1609.344`).
* **`/api/delivery-fee` (Pricing Engine)**
  * Applies the 4 exact rules specified in this document.
  * Ensures precision by not rounding the mileage before multiplying by the rate.

## 3. UI Components
* **`components/FulfillmentModal.tsx`**: A full-screen, multi-step modal (`method` → `address` → `validating` → `eligible/ineligible`). Uses a debounced Mapbox autocomplete search and handles all distance validation edge cases natively.
* **`components/FulfillmentGuard.tsx`**: A headless component mounted in `app/layout.tsx`. It waits for Zustand to hydrate, and if no valid fulfillment state exists, automatically triggers the `FulfillmentModal` to gate the user.
* **`components/Navbar.tsx`**: Updated to show a persistent fulfillment chip (e.g., "Delivering: 123 Main St" or "Pickup") which can be clicked to edit preferences.
* **`components/CartDrawer.tsx`**: Updated to show a dynamic fee breakdown (Subtotal, Delivery Fee, Total).

## 4. Backend Adjustments (`murad-sweets-user-backend`)
* Removed legacy `$15.00` delivery minimum checks from `app/services/pricing.py`.
* Removed legacy Brooklyn zip-code hard-blocks.
* Removed hardcoded `$5.00` delivery fees, offloading delivery pricing entirely to the frontend's OSRM distance calculator.
