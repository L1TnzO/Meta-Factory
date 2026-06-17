import { test } from "node:test";
import assert from "node:assert/strict";
import { summarizeTodos, type Todo } from "./summarize.ts";

test("summarizeTodos: total, done y los titles de los pendientes en orden", () => {
  const todos: Todo[] = [
    { id: 1, title: "comprar pan", done: false },
    { id: 2, title: "lavar", done: true },
    { id: 3, title: "estudiar", done: false },
  ];
  const s = summarizeTodos(todos);
  assert.equal(s.total, 3);
  assert.equal(s.done, 1);
  assert.deepEqual(s.pending, ["comprar pan", "estudiar"]);
});

test("summarizeTodos: lista vacía", () => {
  const s = summarizeTodos([]);
  assert.equal(s.total, 0);
  assert.equal(s.done, 0);
  assert.deepEqual(s.pending, []);
});
