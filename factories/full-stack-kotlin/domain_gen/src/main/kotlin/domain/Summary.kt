package domain

fun summarize(tasks: List<Task>): ProjectSummary {
    val total = tasks.size
    val pending = tasks.filter { !it.done }.map { it.title }
    val done = total - pending.size
    val status = when {
        done == 0 -> ProjectStatus.NotStarted
        total > 0 && done == total -> ProjectStatus.Completed
        else -> ProjectStatus.InProgress
    }
    return ProjectSummary(total, done, pending, status)
}
