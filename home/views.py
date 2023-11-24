from datetime import datetime, timedelta, date
from django.utils import timezone
import jdatetime
from django.utils.dateparse import parse_time
import csv
import io
from django.http import HttpResponse
from .models import WorkSession
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse


def convert_to_24_hour_format(time_str):
    if time_str:
        # Check if the time string includes AM/PM
        if "AM" in time_str or "PM" in time_str:
            return jdatetime.datetime.strptime(time_str, '%I:%M %p').strftime('%H:%M')
        else:
            return time_str
    return None


# Create your views here.
@login_required
def home_view(request):
    today_gregorian = timezone.now()
    today_jalali = jdatetime.date.fromgregorian(date=today_gregorian)
    formatted_date = today_jalali.strftime('%A, %d %B')

    try:
        existing_session = WorkSession.objects.get(user=request.user, date=timezone.now().date())
    except WorkSession.DoesNotExist:
        existing_session = None

    context = {
        'today_jalali': formatted_date,
        'existing_session': existing_session
    }
    return render(request, 'home/home.html', context)


@login_required
def work_session_view(request):
    if request.method == 'POST':
        work_mode = request.POST.get('work_mode')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        # Convert 12-hour time format to 24-hour format
        start_time = parse_time(start_time) if start_time else None
        end_time = parse_time(end_time) if end_time else None

        # Check if a session for today already exists
        session, created = WorkSession.objects.get_or_create(
            user=request.user,
            date=timezone.now().date(),
            defaults={'work_mode': work_mode}
        )

        # Update the start and end times as needed
        if start_time:
            session.start_time = start_time
        if end_time:
            session.end_time = end_time
        session.save()

        messages.success(request, 'Data saved successfully!')
        return redirect('home')

    return render(request, 'home/home.html')


def jalali_to_gregorian(jalali_date_str):
    year, month, day = map(int, jalali_date_str.split('/'))
    jalali_date = jdatetime.date(year, month, day)
    return jalali_date.togregorian()


def calculate_over_under_time(record):
    # Check if start or end time is missing
    if not record.start_time or not record.end_time:
        return "00:00"

    # Convert times to datetime objects for calculation
    start_datetime = datetime.combine(datetime.today(), record.start_time)
    end_datetime = datetime.combine(datetime.today(), record.end_time)

    # Calculate worked duration
    worked_duration = end_datetime - start_datetime

    # Define standard work duration based on the day of the week
    if record.date.weekday() in [0, 1, 2, 5, 6]:  # Saturday to Wednesday
        standard_duration = timedelta(hours=9)
    elif record.date.weekday() == 3:  # Thursday
        standard_duration = timedelta(hours=4)
    else:  # Friday or any other day (if applicable)
        standard_duration = timedelta(hours=0)

    # Calculate over/under time
    over_under_duration = worked_duration - standard_duration

    # Format over/under time as HH:MM
    total_minutes = int(over_under_duration.total_seconds() / 60)
    hours, minutes = divmod(abs(total_minutes), 60)

    # Add sign for under time
    sign = '-' if total_minutes < 0 else ''
    return f"{sign}{hours:02d}:{minutes:02d}"

def get_persian_day_of_week(weekday_number):
    days = ["شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]
    return days[weekday_number]


def download_records(request):
    start_date_jalali = request.GET.get('start_date')
    end_date_jalali = request.GET.get('end_date')

    # Convert Jalali dates to Gregorian
    start_date_gregorian = jalali_to_gregorian(start_date_jalali)
    end_date_gregorian = jalali_to_gregorian(end_date_jalali)

    # Query your database for records between the converted dates
    records = WorkSession.objects.filter(user=request.user, date__range=[start_date_gregorian, end_date_gregorian]).order_by('date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="records.csv"'

    buffer = io.StringIO()
    writer = csv.writer(buffer, dialect='excel')
    writer.writerow(['Date', 'Day', 'Start Time', 'End Time', 'Mode', 'Over/Under Time'])

    for record in records:
        date_jalali = jdatetime.date.fromgregorian(date=record.date)
        day_of_week = get_persian_day_of_week(date_jalali.weekday())

        start_time = record.start_time.strftime("%H:%M")
        end_time = record.end_time.strftime("%H:%M") if record.end_time else ""

        work_mode = 'حضوری' if record.work_mode == 'in_person' else 'دورکاری'

        # Calculate over/under time
        over_under_time = calculate_over_under_time(record)

        writer.writerow(
            [date_jalali.strftime('%Y/%m/%d'), day_of_week, start_time, end_time, work_mode, over_under_time])
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="records.csv"'

    return response
