// app.js
$(document).ready(function () {
    'use strict';

    // Set Luxon's default time zone to Europe/Berlin (Central European Time)
    luxon.Settings.defaultZone = 'Europe/Berlin';

    // Initialize Socket.IO
    const socket = io();

    // Real-Time Chart Initialization
    const realTimeCtx = document.getElementById('real-time-chart').getContext('2d');
    const realTimeChart = new Chart(realTimeCtx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Cars per Minute',
                data: [], // Data points: { x: time, y: count }
                backgroundColor: 'rgba(255, 99, 132, 0.2)', // Red background
                borderColor: 'rgba(255, 99, 132, 1)',       // Red border
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: 3
            }]
        },
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        tooltipFormat: 'dd MMM yyyy HH:mm',
                    },
                    adapters: {
                        date: {
                            zone: 'Europe/Berlin',
                        },
                    },
                    title: {
                        display: true,
                        text: 'Time (CET/CEST)'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Cars'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true
                }
            },
            maintainAspectRatio: false,
            animation: false
        }
    });

    // Variables for real-time data accumulation
    let realTimeCarCounts = {}; // Key: minute in UTC, Value: car count
    let lastCleanup = luxon.DateTime.utc();

    // Handle incoming data from the server
    socket.on('frame', function (data) {
        // Update the video feed
        $('#video-feed').attr('src', 'data:image/jpeg;base64,' + data.frame);

        // Use UTC time for consistent data accumulation
        const currentMinuteUTC = luxon.DateTime.utc().startOf('minute').toISO();

        // Initialize count for the minute if it doesn't exist
        if (!realTimeCarCounts[currentMinuteUTC]) {
            realTimeCarCounts[currentMinuteUTC] = 0;
        }

        // Accumulate car counts
        realTimeCarCounts[currentMinuteUTC] += data.car_count;

        // Update the real-time chart
        updateRealTimeChart();
    });

    // Function to update the real-time chart
    function updateRealTimeChart() {
        const now = luxon.DateTime.now(); // CET/CEST time
        const oneHourAgo = now.minus({ hours: 1 });

        // Prepare chart data
        const chartData = Object.keys(realTimeCarCounts)
            .map(timeStrUTC => {
                // Parse the time string as UTC
                const timeUTC = luxon.DateTime.fromISO(timeStrUTC, { zone: 'utc' });
                // Convert to local time (CET/CEST)
                const timeLocal = timeUTC.setZone('Europe/Berlin');
                return { time: timeLocal, count: realTimeCarCounts[timeStrUTC] };
            })
            .filter(entry => entry.time >= oneHourAgo)
            .sort((a, b) => a.time - b.time);

        // Update chart data
        realTimeChart.data.datasets[0].data = chartData.map(entry => ({
            x: entry.time.toJSDate(),
            y: entry.count
        }));

        realTimeChart.update();

        // Clean up old data every minute
        const nowUTC = luxon.DateTime.utc();
        if (nowUTC.diff(lastCleanup, 'minutes').minutes >= 1) {
            Object.keys(realTimeCarCounts).forEach(timeStrUTC => {
                const timeUTC = luxon.DateTime.fromISO(timeStrUTC, { zone: 'utc' });
                if (timeUTC.plus({ hours: 1 }) < nowUTC) {
                    delete realTimeCarCounts[timeStrUTC];
                }
            });
            lastCleanup = nowUTC;
        }
    }

    // Start Tracking Button Handler
    $('#start-tracking').click(function () {
        $.ajax({
            url: '/start_tracking',
            method: 'POST',
            success: function () {
                alert('Tracking started.');
                realTimeCarCounts = {}; // Reset counts
                updateImage();
            },
            error: function () {
                alert('Error starting tracking.');
            }
        });
    });

    // Stop Tracking Button Handler
    $('#stop-tracking').click(function () {
        $.ajax({
            url: '/stop_tracking',
            method: 'POST',
            success: function () {
                alert('Tracking stopped.');
                realTimeCarCounts = {}; // Reset counts
                updateImage();
            },
            error: function () {
                alert('Error stopping tracking.');
            }
        });
    });

    // Function to update the image based on tracking status
    function updateImage() {
        $.ajax({
            url: '/tracking_status',
            method: 'GET',
            success: function (data) {
                const img = $('#video-feed');
                if (data.tracking_active) {
                    // Tracking is active; image will be updated via 'frame' event
                    img.attr('alt', '');
                } else {
                    // Tracking is not active; display placeholder image or message
                    img.attr('src', '');
                    img.attr('alt', 'Click "Start Tracking" to begin.');
                    img.css('background-color', '#f0f0f0');
                    img.css('display', 'block');
                    img.css('width', '640px');
                    img.css('height', '360px');
                    img.css('line-height', '360px');
                    img.css('text-align', 'center');
                    img.css('color', '#666');
                    img.css('font-size', '18px');
                }
            },
            error: function () {
                console.error('Error fetching tracking status.');
            }
        });
    }

    // Call updateImage on page load
    updateImage();

    // Optionally, check tracking status periodically
    setInterval(updateImage, 5000);
    // Historical Chart Initialization
    const ctx = document.getElementById('traffic-chart').getContext('2d');
    const trafficChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Detected Cars',
                data: [], // Data points
                backgroundColor: 'rgba(54, 162, 235, 0.2)', // Blue background
                borderColor: 'rgba(54, 162, 235, 1)',       // Blue border
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'hour', // Default unit
                        tooltipFormat: 'dd MMM yyyy HH:mm',
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'dd MMM HH:mm',
                            day: 'dd MMM',
                            month: 'MMM yyyy'
                        }
                    },
                    adapters: {
                        date: {
                            zone: 'Europe/Berlin',
                        },
                    },
                    title: {
                        display: true,
                        text: 'Time (CET/CEST)'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Cars'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true
                }
            },
            maintainAspectRatio: false,
            animation: false
        }
    });

    // Initialize Flatpickr for date-time inputs
    flatpickr('#start-date', {
        enableTime: true,
        dateFormat: 'Y-m-d H:i',
        defaultDate: luxon.DateTime.now().minus({ days: 1 }).toJSDate(),
        time_24hr: true
    });

    flatpickr('#end-date', {
        enableTime: true,
        dateFormat: 'Y-m-d H:i',
        defaultDate: luxon.DateTime.now().toJSDate(),
        time_24hr: true
    });

    // Map granularity values to Chart.js time units
    const granularityUnitMap = {
        '5': 'minute',
        '30': 'minute',
        '60': 'hour'
    };

    // Fetch initial historical data when the page loads (past 24 hours by default)
    const defaultEndDate = luxon.DateTime.now();
    const defaultStartDate = defaultEndDate.minus({ days: 1 });
    const defaultGranularity = '60'; // Hourly granularity

    fetchHistoricalData(defaultStartDate, defaultEndDate, defaultGranularity);

    // Function to fetch historical data based on selected date range and granularity
    function fetchHistoricalData(startDate, endDate, granularity) {
        // Show loading spinner or disable fetch button if implemented
        $.ajax({
            url: '/historical_data',
            method: 'GET',
            data: {
                start_date: startDate.toUTC().toISO({ suppressMilliseconds: true }),
                end_date: endDate.toUTC().toISO({ suppressMilliseconds: true }),
                granularity: granularity
            },
            success: function (data) {
                if (data.error) {
                    alert(data.error);
                    return;
                }
                if (data.length === 0) {
                    alert('No data available for the selected date range.');
                    // Clear existing chart data
                    trafficChart.data.datasets[0].data = [];
                    trafficChart.update();
                    return;
                }

                // Clear existing chart data
                trafficChart.data.datasets[0].data = [];

                // Add data to the chart and calculate total cars
                let totalCars = 0;
                data.forEach(function (entry) {
                    // Parse the timestamp as UTC
                    const timeUTC = luxon.DateTime.fromISO(entry.time, { zone: 'utc' });
                    // Convert to Europe/Berlin time zone
                    const timeLocal = timeUTC.setZone('Europe/Berlin').plus({ hours: 1 });

                    trafficChart.data.datasets[0].data.push({
                        x: timeLocal.toJSDate(),
                        y: entry.total_cars
                    });
                    totalCars += entry.total_cars;
                });

                // Update chart options based on granularity
                trafficChart.options.scales.x.time.unit = granularityUnitMap[granularity] || 'hour';

                // Update the chart
                trafficChart.update();

                // Update the total cars display
                $('#total-cars').text(totalCars);
            },
            error: function () {
                alert('Error fetching historical data.');
            }
        });
    }

    // Handle date range and granularity selection, and fetch data
    $('#fetch-data').click(function () {
        const startDateStr = $('#start-date').val();
        const endDateStr = $('#end-date').val();
        const granularity = $('#granularity').val();

        if (!startDateStr || !endDateStr) {
            alert('Please select both start and end dates.');
            return;
        }

        // Parse dates in Europe/Berlin time zone
        const startDate = luxon.DateTime.fromFormat(startDateStr, 'yyyy-MM-dd HH:mm', { zone: 'Europe/Berlin' });
        const endDate = luxon.DateTime.fromFormat(endDateStr, 'yyyy-MM-dd HH:mm', { zone: 'Europe/Berlin' });

        if (!startDate.isValid || !endDate.isValid) {
            alert('Invalid date format.');
            return;
        }

        if (startDate >= endDate) {
            alert('Start date must be before end date.');
            return;
        }

        fetchHistoricalData(startDate, endDate, granularity);
    });

    // Existing code for updating the image based on tracking status
    // updateImage() function is already defined in Part 1

    // Call updateImage on page load
    updateImage();

    // Optionally, check tracking status periodically
    setInterval(updateImage, 5000);
});

