# Copyright 2020 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class BookableMixin(models.AbstractModel):
    _name = "bookable.mixin"
    _description = "Bookable Mixin"

    slot_duration = fields.Float()
    slot_capacity = fields.Integer()

    def _get_slot_duration(self):
        return self.slot_duration

    def _get_slot_capacity(self):
        return self.slot_capacity

    def _get_booked_slot(self, start, stop):
        domain = self._get_booking_domain(start, stop)
        return self.env["calendar.event"].search(
            expression.AND([domain, [("booking_type", "=", "booked")]])
        )

    def _build_timeline_load(self, start, stop):
        """
        :return: list of tuples of format (datetime, load)
        """
        timeline = defaultdict(int)
        timeline.update({start: 0, stop: 0})
        for booked_slot in self._get_booked_slot(start, stop):
            if booked_slot.start < start:
                timeline[start] += 1
            else:
                timeline[booked_slot.start] += 1
            if booked_slot.stop < stop:
                timeline[booked_slot.stop] -= 1

        timeline = list(timeline.items())
        timeline.sort()
        return timeline

    def _get_available_slot(self, start, stop):
        load_timeline = self._build_timeline_load(start, stop)

        load = 0
        slots = []
        slot = None
        capacity = self._get_slot_capacity()

        for dt, load_delta in load_timeline:
            load += load_delta
            if not slot and load < capacity:
                slot = [dt, None]
                slots.append(slot)
            elif slot:
                slot[1] = dt
                if load >= capacity:
                    slot = None
        return slots

    def _prepare_bookable_slot(self, open_slot, start, stop):
        # If needed you can inject extra information from the open_slot
        return {"start": start, "stop": stop}

    def _build_bookable_slot(self, open_slot, start, stop):
        bookable_slots = []
        delta = self._get_slot_duration()
        while True:
            slot_stop = start + relativedelta(minutes=delta)
            if slot_stop > stop:
                break
            bookable_slots.append(
                self._prepare_bookable_slot(open_slot, start, slot_stop)
            )
            start += relativedelta(minutes=delta)
        return bookable_slots

    def get_open_slot(self, start, stop):
        """
        :return: all bookable slots
        """
        domain = self._get_booking_domain(start, stop)
        domain = expression.AND([domain, [("booking_type", "=", "bookable")]])
        return self.env["calendar.event"].search(domain, order="start_date")

    def get_bookable_slot(self, start, stop):
        """
        :return: bookable slots that are free (that are currently under capacity)
        """
        start = fields.Datetime.to_datetime(start)
        stop = fields.Datetime.to_datetime(stop)

        slots = []
        openslots = self.get_open_slot(start, stop)
        for open_slot in openslots:
            for slot_start, slot_stop in self._get_available_slot(
                max(open_slot.start, start), min(open_slot.stop, stop)
            ):
                slots += self._build_bookable_slot(open_slot, slot_start, slot_stop)
        return slots

    def _get_domain_for_current_object(self):
        return [
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
        ]

    def _get_booking_domain(self, start, stop):
        domain = self._get_domain_for_current_object()
        return expression.AND(
            [
                domain,
                [
                    "|",
                    "&",
                    ("start", ">=", start),
                    ("start", "<", stop),
                    "&",
                    ("stop", ">", start),
                    ("stop", "<=", stop),
                ],
            ]
        )

    def _check_load(self, start, stop):
        load_timeline = self._build_timeline_load(start, stop)
        capacity = self._get_slot_capacity()
        load = 0
        for _dt, load_delta in load_timeline:
            load += load_delta
            if load > capacity:
                raise UserError(_("The slot is not available anymore"))

    def _prepare_booked_slot(self, vals):
        vals.update(
            {
                "res_model_id": self.env["ir.model"]
                .search([("model", "=", self._name)])
                .id,
                "res_id": self.id,
                "booking_type": "booked",
                "start": fields.Datetime.to_datetime(vals["start"]),
                "stop": fields.Datetime.to_datetime(vals["stop"]),
            }
        )
        return vals

    def _check_duration(self, start, stop):
        duration = (stop - start).total_seconds() / 60.0
        if duration != self._get_slot_duration():
            raise UserError(_("The slot duration is not valid"))

    def _check_on_open_slot(self, start, stop):
        domain = self._get_domain_for_current_object()
        domain = expression.AND([(domain, [("booking_type", "=", "bookable")])])
        domain = expression.AND(
            [
                domain,
                [
                    ("start", "<=", start),
                    ("stop", ">=", stop),
                ],
            ]
        )
        open_slot = self.env["calendar.event"].search(domain)
        if not open_slot:
            raise UserError(_("The slot is not on a bookable zone"))

    def book_slot(self, vals):
        self.ensure_one()
        vals = self._prepare_booked_slot(vals)
        self._check_on_open_slot(vals["start"], vals["stop"])
        self._check_duration(vals["start"], vals["stop"])
        slot = self.env["calendar.event"].create(vals)
        self._check_load(vals["start"], vals["stop"])
        return slot
