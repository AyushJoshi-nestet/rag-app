# HNSW (Hierarchical Navigable Small World): Complete Overview

## What is HNSW?

HNSW is a graph-based indexing algorithm used by vector databases such as Qdrant to perform **Approximate Nearest Neighbor (ANN)** search efficiently.

Instead of comparing a query against every vector (brute force), HNSW organizes vectors into multiple graph layers that allow the search to quickly narrow down promising regions before performing a detailed search.

---

# 1. Structure (How the Graph is Built)

## Layer Organization

HNSW consists of multiple layers arranged like floors of a building.

- **Layer 0 (Ground Floor)**
  - Contains **100% of all vectors**.
  - Every inserted vector always exists here.
  - This is the only layer containing the complete dataset.

- **Higher Layers (Layer 1, Layer 2, Layer 3, ...)**
  - Each higher layer contains a progressively smaller random subset of vectors.
  - The probability of appearing decreases exponentially with height.
  - These upper layers provide a sparse representation of the graph.

Example:

```text
Layer 3 :      •      •
Layer 2 :    •   •      •
Layer 1 :  • • • • • •
Layer 0 : • • • • • • • • • •
```

---

## Random Layer Assignment

When a vector is inserted:

- A random level (maximum layer) is assigned.
- The assignment is completely random.
- It is **not based on the vector's content or similarity**.

For example:

| Vector | Assigned Layers |
|---------|-----------------|
| A | 0 |
| B | 0,1 |
| C | 0,1,2 |
| D | 0 |
| E | 0,1,2,3 |

---

## Same Vector on Multiple Layers

A vector may exist on several layers simultaneously.

Important:

- It is still the **same vector**.
- It has the **same ID**.
- It stores the **same embedding**.

The only thing that changes between layers is its graph connections.

Example:

```text
Layer 2

      C
     / \
    A   E

Layer 1

A ---- B ---- C
 \      |
  \     |
    D --E

Layer 0

A--B--C--D--E--F--G
```

Since each layer contains different subsets of vectors, the neighbors of the same vector differ from one layer to another.

---

# 2. Insertion Process

When adding a new vector, HNSW builds connections layer by layer.

## Step 1 — Assign Random Height

Choose the maximum layer where the new vector will exist.

Example:

```text
New Vector X

Exists on:
Layer 2
Layer 1
Layer 0
```

---

## Step 2 — Start from the Entry Point

Every HNSW graph maintains a fixed **entry point**, typically located on the highest layer.

Search always begins here.

```text
Entry Point
      |
      v
Layer 3
```

---

## Step 3 — Greedy Search on Current Layer

Compare the new vector with:

- the current node
- all neighboring nodes

Move to whichever neighbor is closer.

Repeat until no neighbor is closer.

This greedy search finds the best local position on that layer.

---

## Step 4 — Descend to the Next Layer

Once the best node is found:

- Stay on that node.
- Move down one layer.

Think of this like taking an elevator.

```text
Layer 3

      A
      |
      |
Layer 2

      A
```

The node remains the same; only the layer changes.

---

## Step 5 — Repeat Until Layer 0

Continue:

1. Greedy search
2. Descend
3. Greedy search
4. Descend

until reaching Layer 0.

---

## Step 6 — Create Connections

At every layer where the new vector exists:

- Find the best candidate neighbors.
- Connect the vector to its **top M nearest neighbors**.

Example:

```text
Before

A ----- B

After inserting X

A ---- X ---- B
      |
      C
```

The parameter **M** controls the maximum number of neighbors per node.

---

# 3. Search Process

Searching follows nearly the same path as insertion.

---

## Step 1 — Start at the Entry Point

Begin at the highest layer.

```text
Entry Point
      |
Layer 3
```

---

## Step 2 — Greedy Navigation

For the query vector:

- Compare with the current node.
- Compare with neighboring nodes.
- Move to the closest neighbor.
- Repeat until no improvement is possible.

---

## Step 3 — Descend One Layer

The best node found becomes the starting point for the next lower layer.

No restart is needed.

```text
Layer 3

Best Node = A

↓

Layer 2

Start from A
```

---

## Step 4 — Continue Through Every Layer

Repeat the same process for:

- Layer 3
- Layer 2
- Layer 1
- Layer 0

Each lower layer performs a more refined search.

---

## Step 5 — Final Search on Layer 0

Layer 0 contains every vector.

Here the search verifies the nearest neighbors using the complete graph.

When no neighboring node improves the result, the search ends.

The current best node(s) become the approximate nearest neighbors.

---

# 4. Why the Search Doesn't Stop Early

Even if an upper layer finds a seemingly excellent match, the algorithm continues downward.

Reason:

Upper layers only contain random subsets of vectors.

A closer vector may exist on a lower layer that wasn't present above.

Only Layer 0 includes every vector.

Therefore, the final verification always happens there.

---

# 5. Why HNSW is Fast

The hierarchy divides the search into two phases.

## Upper Layers

- Few vectors
- Long-distance jumps
- Quickly narrow the search region

Think of them as highways.

---

## Lower Layers

- Many vectors
- Dense graph
- Short local movements
- Fine-grained search

Think of them as city streets.

---

Instead of checking millions of vectors, HNSW:

1. Quickly moves into the correct neighborhood.
2. Performs a detailed search only within that region.

This dramatically reduces computation while maintaining high accuracy.

---

# Complete Search Flow

```text
               Query
                 │
                 ▼
        Start at Entry Point
                 │
                 ▼
        Greedy Search (Top Layer)
                 │
                 ▼
            Descend
                 │
                 ▼
        Greedy Search
                 │
                 ▼
            Descend
                 │
                 ▼
        Greedy Search
                 │
                 ▼
            Layer 0
                 │
                 ▼
      Verify Nearest Neighbors
                 │
                 ▼
           Return Results
```

---

# Key Takeaways

- Every vector always exists on **Layer 0**.
- Higher layers contain random, progressively smaller subsets of vectors.
- A vector may exist on multiple layers with different graph neighbors.
- Insertion and search both use greedy navigation from the top layer downward.
- Each layer's best node becomes the starting point for the next lower layer.
- Search never stops before reaching Layer 0 because only Layer 0 contains the complete dataset.
- Upper layers provide fast global navigation, while Layer 0 provides precise local refinement.
- This hierarchical approach enables vector databases like **Qdrant** to search millions of embeddings in milliseconds instead of performing an exhaustive scan.