# Other pages: live against branch, where the main content differs

## data/index.html

```diff
--- live
+++ branch
@@ -1204,2 +1204,14 @@
 e84dc2c80137</code>
+</td>
+</tr>
+<tr>
+<td>
+<a href="../data/v3/learning-pilot.json">
+data/v3/learning-pilot.json</a>
+</td>
+<td class="num">
+21,976</td>
+<td>
+<code>
+a94ac16871e1</code>
 </td>
```

## method/index.html

```diff
--- live
+++ branch
@@ -5443,32 +5443,2 @@
 </li>
-<li>
-i) <strong>
-Late entries, exploratory, dated 2026-11-07 (Ümit&#x27;s go, bus #2646; written and committed before any model call of the setups below).</strong>
- Eight league late entries are added: SubQ Snap 1.1, Base Labs Elephant-1, Base Labs Mammoth-1, Drex Max 1.1, Drex 2.0, Drex Max v1, Drex 2.0 (local) and REAX 1.3 (REAX 1.3 only if Can approves reusing its container exception; until then it is not run).<ul>
-<li>
-<strong>
-Exploratory, no group.</strong>
- They are not Cup-roster additions under (b)/(g). Like Gemini 4 Argon (low) under (h), they belong to no group: they enter no primary comparison and do not change M (M stays 5).</li>
-<li>
-<strong>
-Timing, stated wherever these results appear:</strong>
- they are added after this test&#x27;s results had been computed and read (2026-10-27/28, and the additions of 2026-10-28).</li>
-<li>
-<strong>
-Same rules and scoring as every setup:</strong>
- the frozen pairs, prompts (<code>
-bg-v3-std-notable</code>
- / <code>
-bg-v3-nack</code>
-), option-order seed, each setup&#x27;s stored league settings and option cap, the invalid-answer rule of 10.8, the output-limit rule of (h), the stopping rule (b) of 10.8 (400 main positions first, then the 600 reserve when the first look calls for it), and the 10.12 engine check (their new plays on the 40 frozen pairs rolled out with the 10.12 settings).</li>
-<li>
-<strong>
-Unchanged:</strong>
- the 28 published setups and their results (<code>
-results/</code>
-, <code>
-results-2026-10-28/</code>
-). The late entries&#x27; results go to a separate results directory and a separate dated section.</li>
-</ul>
-</li>
 </ul>
@@ -5852,4 +5822,4 @@
 <h2 id="learning-title">
-Learning from experience <span class="status status-not-measured">
-Not measured</span>
+Learning from experience <span class="status status-running">
+Running (preliminary)</span>
 </h2>
@@ -5857,3 +5827,5 @@
 <p>
-Every decision is a separate request; models are not told how earlier games went.</p>
+Running (preliminary): see <a href="../learning/">
+Learning across games</a>
+.</p>
 
```
