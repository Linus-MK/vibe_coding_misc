document.addEventListener('DOMContentLoaded', () => {
    const taskContainer = document.getElementById('task-container');
    
    if (taskContainer) {
        let prepTime = parseInt(taskContainer.dataset.prepTime, 10);
        let durationTime = parseInt(taskContainer.dataset.durationTime, 10) * 60; // convert minutes to seconds
        
        const timerDisplay = document.getElementById('timer');
        const timerStatus = document.getElementById('timer-status');
        
        let timerInterval;

        const formatTime = (seconds) => {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        };

        const startTimer = (initialSeconds, onComplete) => {
            let seconds = initialSeconds;
            timerInterval = setInterval(() => {
                timerDisplay.textContent = formatTime(seconds);
                if (seconds <= 0) {
                    clearInterval(timerInterval);
                    if (onComplete) {
                        onComplete();
                    }
                }
                seconds--;
            }, 1000);
        };

        const startExecTimer = () => {
            timerStatus.textContent = "実行中！";
            timerStatus.style.color = 'var(--accent-color)';
            startTimer(durationTime, () => {
                timerStatus.textContent = "お疲れ様でした！";
                alert('タスク完了！');
            });
        };

        const startPrepTimer = () => {
            timerStatus.textContent = "準備して！";
            timerStatus.style.color = 'inherit';
            startTimer(prepTime, startExecTimer);
        };
        
        startPrepTimer(); // Start the timer sequence automatically

        const rerollButton = document.getElementById('reroll-btn');
        rerollButton.addEventListener('click', async () => {
            try {
                const response = await fetch('/api/random-task');
                if (!response.ok) {
                    throw new Error('タスクの再抽選に失敗しました。');
                }
                const newTask = await response.json();

                if(newTask.error) {
                    alert(newTask.error);
                    return;
                }
                
                // Update view with new task data
                document.getElementById('task-name').textContent = newTask.name;
                const urlContainer = document.getElementById('task-url-container');
                const urlLink = document.getElementById('task-url');
                if (newTask.url) {
                    urlLink.href = newTask.url;
                    urlLink.textContent = newTask.url;
                    urlContainer.style.display = 'block';
                } else {
                    urlContainer.style.display = 'none';
                }

                // Update dataset values
                taskContainer.dataset.taskId = newTask.id;
                taskContainer.dataset.taskName = newTask.name;
                taskContainer.dataset.prepTime = newTask.prep_time_seconds;
                taskContainer.dataset.durationTime = newTask.duration_minutes;
                taskContainer.dataset.taskUrl = newTask.url || '';

                // Reset and restart timer
                clearInterval(timerInterval);
                prepTime = parseInt(newTask.prep_time_seconds, 10);
                durationTime = parseInt(newTask.duration_minutes, 10) * 60;
                startPrepTimer();

            } catch (error) {
                console.error('Error:', error);
                alert('エラーが発生しました。');
            }
        });
    }
});
