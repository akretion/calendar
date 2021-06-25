Abstract module for booking support.
You can use the mixin "BookableMixin" to add booking functionality on your model.

There are several concepts in action, taking a barber shop as an example:

* a slot is represented by a calendar.event

* a *bookable* (a.k.a, *open*) slot represents a time range in which we can make bookings
  (e.g barbershop is open from 2pm to 6pm)

* an *available* slot represents a time range that can be booked (e.g we have a free barber from 2pm to 2.30pm)

* a *booked* slot represents a time range in which the slot is occupied (e.g barber is busy from 2pm to 2.30pm)

* there is a concept of load/capacity (e.g we have 2 barbers so we can have 2 bookings from 2pm to 2.30pm)
