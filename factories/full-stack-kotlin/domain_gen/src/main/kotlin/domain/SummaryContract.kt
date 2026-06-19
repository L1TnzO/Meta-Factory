package domain

import kotlin.system.exitProcess

/** El contract test (DES-8): EJERCITA la lógica generada (summarize). Un stub o una implementación
 *  incorrecta hace exitProcess(1) → gradle `run` rojo. Es el tooth de MAT-2: domain vacío BLOQUEA. */
private fun ensure(cond: Boolean, msg: String) {
    if (!cond) {
        System.err.println("CONTRACT FAIL: $msg")
        exitProcess(1)
    }
}

fun main() {
    val mixed = listOf(
        Task("disenar el schema", true),
        Task("implementar el handler", false),
        Task("documentar la API", false),
    )
    val s = summarize(mixed)
    ensure(s.total == 3, "total esperado 3, fue ${s.total}")
    ensure(s.done == 1, "done esperado 1, fue ${s.done}")
    ensure(
        s.pending == listOf("implementar el handler", "documentar la API"),
        "pending order: ${s.pending}",
    )
    ensure(s.status == ProjectStatus.InProgress, "status esperado InProgress, fue ${s.status}")

    val empty = summarize(emptyList())
    ensure(empty.total == 0 && empty.done == 0 && empty.pending.isEmpty(), "empty counts: $empty")
    ensure(empty.status == ProjectStatus.NotStarted, "empty status: ${empty.status}")

    val allDone = summarize(listOf(Task("a", true), Task("b", true)))
    ensure(allDone.status == ProjectStatus.Completed, "allDone status: ${allDone.status}")
    ensure(allDone.pending.isEmpty(), "allDone pending: ${allDone.pending}")

    val noneDone = summarize(listOf(Task("x", false), Task("y", false)))
    ensure(noneDone.status == ProjectStatus.NotStarted, "noneDone status: ${noneDone.status}")
    ensure(noneDone.pending == listOf("x", "y"), "noneDone pending: ${noneDone.pending}")

    println("FSK_DOMAIN_CONTRACT_OK")
}
