# TaskManager
A simple task manager based on the [todo.txt](https://github.com/todotxt/todo.txt) format using [wxPython](https://wxpython.org/).

![](https://github.com/todotxt/todo.txt/raw/master/description.svg)
It makes the following additions:

1. Recurring tasks that occur on a fixed day every week/month/year are specified as
   D-[mon|tue|wed|thu|fri|sat|sun|day]-[m|y]. 
   
   For example, a task that occurs on the first Monday of every month is specified as 1-mon-m.
   A task that occurs on the last Sunday of every month is specified as L-sun-m.

2. Completion of all occurrences of a recurring task is indicated by prepending a '#x' to the task.

   This is a task for which the last occurrence has been completed:
   ``` x 2021-11-30 Some task due:2021-12-01 rec:1m```

   This is a task for which all occurrences have been completed:
   ``` #x 2021-11-30 A fully completed task due:2021-12-01 rec:1m```
   
3. A line that starts with '#' but not '#x' is a comment and is ignored. All comments are preserved in the file.

4. A deleted task is prepended with '##-' and is treated as a comment.
