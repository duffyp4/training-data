<link rel="stylesheet" href="training-data.css">

# 🏃‍♂️ Training Data Dashboard

Comprehensive training data with detailed per-split metrics, workout data, and wellness information.


<div class="stats-dashboard">
    <h2>📊 October 2025 Quick Stats</h2>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number">2</div>
            <div class="stat-label">Total Workouts</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">6.0</div>
            <div class="stat-label">Miles</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">1.0</div>
            <div class="stat-label">Hours</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">71</div>
            <div class="stat-label">Avg Sleep Score</div>
        </div>
    </div>
</div>



<div class="calendar-widget">
    <h2>📅 Calendar Navigator</h2>
    <div class="calendar-header">
        <button class="calendar-nav" onclick="changeMonth(-1)">‹</button>
        <h3 id="calendar-month">October 2025</h3>
        <button class="calendar-nav" onclick="changeMonth(1)">›</button>
    </div>
    <div class="calendar-grid">
        <div class="calendar-day-header">Sun</div>
        <div class="calendar-day-header">Mon</div>
        <div class="calendar-day-header">Tue</div>
        <div class="calendar-day-header">Wed</div>
        <div class="calendar-day-header">Thu</div>
        <div class="calendar-day-header">Fri</div>
        <div class="calendar-day-header">Sat</div>

        <div class="calendar-day empty"></div>
        <div class="calendar-day empty"></div>
        <div class="calendar-day empty"></div>
        <div class="calendar-day has-data" onclick="window.location.href='data/2025/10/01.html'">
            <span class="day-number">1</span>
            <div class="day-dots"><span class="dot workout-dot">🟢</span><span class="dot wellness-dot">🔵</span></div>
        </div>
        <div class="calendar-day has-data" onclick="window.location.href='data/2025/10/02.html'">
            <span class="day-number">2</span>
            <div class="day-dots"><span class="dot workout-dot">🟢</span><span class="dot wellness-dot">🔵</span></div>
        </div>
        <div class="calendar-day has-data" onclick="window.location.href='data/2025/10/03.html'">
            <span class="day-number">3</span>
            <div class="day-dots"><span class="dot wellness-dot">🔵</span></div>
        </div>
        <div class="calendar-day">
            <span class="day-number">4</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">5</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">6</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">7</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">8</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">9</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">10</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">11</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">12</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">13</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">14</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">15</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">16</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">17</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">18</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">19</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">20</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">21</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">22</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">23</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">24</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">25</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">26</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">27</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">28</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">29</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">30</span>
        </div>
        <div class="calendar-day">
            <span class="day-number">31</span>
        </div>
        <div class="calendar-day empty"></div>
    </div>
    <div class="calendar-legend">
        <span><span class="dot">🟢</span> Workout Data</span>
        <span><span class="dot">🔵</span> Wellness Data</span>
    </div>
</div>


<div class="training-plan">
    <h2>🏃‍♂️ Weekly Training vs Hal Higdon Novice 2</h2>
    <div class="training-cards">

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 1</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Jun 08 - Jun 14</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">14.3 miles</span>
                    <span class="target-miles">Target: 19 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">5</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 2</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Jun 15 - Jun 21</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">11.1 miles</span>
                    <span class="target-miles">Target: 20 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">3</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card hit-target">
            <div class="training-card-header">
                <h4>Week 3</h4>
                <span class="status-icon">✅</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Jun 22 - Jun 28</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">17.8 miles</span>
                    <span class="target-miles">Target: 17 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">6</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 4</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Jun 29 - Jul 05</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">13.5 miles</span>
                    <span class="target-miles">Target: 23 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">5</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card hit-target">
            <div class="training-card-header">
                <h4>Week 5</h4>
                <span class="status-icon">✅</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Jul 06 - Jul 12</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">24.0 miles</span>
                    <span class="target-miles">Target: 24 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">7</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card hit-target">
            <div class="training-card-header">
                <h4>Week 6</h4>
                <span class="status-icon">✅</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Jul 13 - Jul 19</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">33.2 miles</span>
                    <span class="target-miles">Target: 21 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">6</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 7</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Jul 20 - Jul 26</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">25.0 miles</span>
                    <span class="target-miles">Target: 29 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">5</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 8</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Jul 27 - Aug 02</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">28.6 miles</span>
                    <span class="target-miles">Target: 30 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">4</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card hit-target">
            <div class="training-card-header">
                <h4>Week 9</h4>
                <span class="status-icon">✅</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Aug 03 - Aug 09</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">25.2 miles</span>
                    <span class="target-miles">Target: 15 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">3</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 10</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Aug 10 - Aug 16</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">12.1 miles</span>
                    <span class="target-miles">Target: 33 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">2</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 11</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Aug 17 - Aug 23</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">34.3 miles</span>
                    <span class="target-miles">Target: 36 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">4</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 12</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Aug 24 - Aug 30</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">21.4 miles</span>
                    <span class="target-miles">Target: 31 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">2</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 13</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Aug 31 - Sep 06</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">31.8 miles</span>
                    <span class="target-miles">Target: 34 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">6</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 14</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Sep 07 - Sep 13</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">29.3 miles</span>
                    <span class="target-miles">Target: 32 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">3</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card missed-target">
            <div class="training-card-header">
                <h4>Week 15</h4>
                <span class="status-icon">❌</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Sep 14 - Sep 20</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">29.8 miles</span>
                    <span class="target-miles">Target: 40 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">4</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card hit-target">
            <div class="training-card-header">
                <h4>Week 16</h4>
                <span class="status-icon">✅</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Sep 21 - Sep 27</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">32.1 miles</span>
                    <span class="target-miles">Target: 20 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">6</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="training-card current-week">
            <div class="training-card-header">
                <h4>Week 17</h4>
                <span class="status-icon">🔄</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">Sep 28 - Oct 04</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">6.0 miles</span>
                    <span class="target-miles">Target: 12 miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">2</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>


<script>
let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();

function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    } else if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    }
    
    const monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"];
    
    document.getElementById('calendar-month').textContent = 
        monthNames[currentMonth] + ' ' + currentYear;
    
    // Note: Full calendar regeneration would require server-side update
    // For now, this updates the header. Full implementation would require AJAX.
}
</script>