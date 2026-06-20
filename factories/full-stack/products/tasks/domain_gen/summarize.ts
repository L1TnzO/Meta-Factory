export interface Todo {
  id: number;
  title: string;
  done: boolean;
}

export function summarizeTodos(todos: Todo[]): { total: number; done: number; pending: string[] } {
  let done = 0;
  const pending: string[] = [];
  for (const todo of todos) {
    if (todo.done === true) {
      done++;
    } else {
      pending.push(todo.title);
    }
  }
  return { total: todos.length, done, pending };
}
