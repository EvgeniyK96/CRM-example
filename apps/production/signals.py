from django.dispatch import Signal

# task — задание запущено, сырьё списано (task.consumptions)
task_started = Signal()
# task — задание завершено (task.raw_cost, task.output_lot)
task_finished = Signal()
