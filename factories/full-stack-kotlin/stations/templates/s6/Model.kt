package domain

/** Una tarea de un proyecto (espejo del dominio Task del blueprint domain.product). */
data class Task(val title: String, val done: Boolean)

/** Estado de avance de un proyecto. sealed ⇒ el `when` que lo consume es exhaustivo (dureza, DES-10). */
sealed interface ProjectStatus {
    data object NotStarted : ProjectStatus
    data object InProgress : ProjectStatus
    data object Completed : ProjectStatus
}

/** Resumen de avance derivado de las tareas de un proyecto (lo que `summarize` produce). */
data class ProjectSummary(
    val total: Int,
    val done: Int,
    val pending: List<String>,
    val status: ProjectStatus,
)
