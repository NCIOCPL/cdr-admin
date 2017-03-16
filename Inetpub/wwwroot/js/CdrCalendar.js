/*
 * Modeled after the calendar used in Django.
 *
 * JavaScript calendar.  In order to have a form field use the calendar
 * widget, you need to load this script in your HTML header block,
 * load the CdrCalendar.css rules, and attach the CdrDateField class
 * to the input element for the field:
 *
 * <html>
 *  <head>
 *   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
 *   <script language='JavaScript' src='/js/CdrCalendar.js'></script>
 *  </head>
 *  <body>
 *   <form ...>
 *    <input class="CdrDateField" name=... />
 *   </form>
 *  </body>
 * </html>
 */

var CdrCalendar = {
    setReadOnly: true,
    cals: [],
    fields: [],
    calBoxIdBase: 'cdrcalbox',   // ID for block that gets shown/hidden
    calMainIdBase: 'cdrcalmain', // ID for block that get populated by draw()
    images_dir: '/images',
    months: ('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec').split(' '),
    days: ('S M T W T F S').split(' '),
    ie: navigator.userAgent.indexOf("MSIE") > -1,
    sticky: 0, // 0=no 1=remember last for each cal 2=remember globally
    month: undefined, // for sticky=2
    year: undefined, // for sticky=2

    // Attach a calendar interface for an input field.
    addCalendar: function(field) {

        field.title = "Click calendar to edit this field ...";
        // Don't want the user to edit the field directly.
        if (CdrCalendar.setReadOnly)
            field.readOnly = "1";

        // Remember the input field.
        var num = CdrCalendar.cals.length;
        CdrCalendar.fields[num] = field;

        // Create the link to open the calendar for this field.
        var img = CdrCalendar.addCalendarLink(num, field);

        // Create the outer block for the displayed calendar.
        var calBox = CdrCalendar.makeCalBox(num);

        // Add navigation links at the top.
        calBox.appendChild(CdrCalendar.makeNavBox(num));

        // Add the main box into which the calendar table is populated.
        var mainBox       = document.createElement('div');
        var divName       = CdrCalendar.calMainIdBase + num;
        mainBox.className = 'cdr-cal-main';
        mainBox.setAttribute('id', divName);
        calBox.appendChild(mainBox);

        // Create and draw the new Calendar object.
        CdrCalendar.cals[num] = new CdrCalendar.Calendar(num, calBox, img);
        //CdrCalendar.cals[num].draw();
    },

    makeCalBox: function(num) {
        var box            = document.createElement('div');
        box.style.display  = 'none';
        box.style.position = 'absolute';
        box.style.zIndex   = "1";
        box.className      = 'cdr-cal-box';
        box.setAttribute('id', CdrCalendar.calBoxIdBase + num);
        document.body.appendChild(box);
        CdrCalendar.addEvent(box, 'click', CdrCalendar.stopPropagation);
        return box;
    },

    makeNavBox: function(num) {
        var box          = document.createElement('div');
        var prev         = document.createElement('span');
        var next         = document.createElement('span');
        box.className    = 'cdr-cal-nav';
        prev.style.left  = "0";
        next.style.right = "0";
        box.appendChild(prev);
        box.appendChild(next);
        prev.appendChild(CdrCalendar.addNavLink('\u00ab', 'prevYear',  num));
        prev.appendChild(CdrCalendar.addNavLink('\u2039', 'prevMonth', num));
        next.appendChild(CdrCalendar.addNavLink('\u203a', 'nextMonth', num));
        next.appendChild(CdrCalendar.addNavLink('\u00bb', 'nextYear',  num));
        return box;
    },
    addNavLink: function(symbol, func, num) {
        var link = document.createElement('a');
        var text = document.createTextNode(symbol);
        var href = 'javascript:CdrCalendar.' + func + '(' + num + ');';
        link.appendChild(text);
        link.setAttribute('href', href);
        link.style.textDecoration = "none";
        link.className = 'cdr-cal-nav-link';
        return link;
    },
    addCalendarLink: function(num, field) {
        var link = document.createElement('a');
        var img  = document.createElement('img');
        var href = 'javascript:CdrCalendar.openCalendar(' + num + ');';
        var src  = CdrCalendar.images_dir + '/CdrCalendarIcon.gif';
        link.className = 'cdr-cal-link';
        link.appendChild(img);
        link.setAttribute('href', href);
        img.setAttribute('alt', 'Calendar');
        img.setAttribute('src', src);
        field.parentNode.insertBefore(link, field.nextSibling);
        return img;
    },

    isLeapYear: function(y) {
        return y % 4 == 0 && y % 100 != 0 || y % 400 == 0;
    },
    getDaysInMonth: function(m, y) {
        if (m == 4 || m == 6 || m == 9 || m == 11)
            return 30;
        else if (m == 2) {
            if (CdrCalendar.isLeapYear(y))
                return 29;
            return 28;
        }
        return 31;
    },
    getTwoDigitString: function(v) {
        return v < 10 ? '0' + '' + v : v;
    },
    makeIsoDate: function(y, m, d) {
        return y + '-' + CdrCalendar.getTwoDigitString(m)
                 + '-' + CdrCalendar.getTwoDigitString(d);
    },
    addEvent: function(o, t, f) {
        if (o.addEventListener) {
            o.addEventListener(t, f, false);
            return true;
        }
        else if (o.attachEvent) {
            var result = o.attachEvent("on" + t, f);
            return result;
        }
        else
            return false;
    },
    addElement: function(name, parentElement) {
        var element = document.createElement(name);
        parentElement.appendChild(element);
        return element;
    },
    addTextNode: function(textValue, element) {
        var textNode = document.createTextNode(textValue);
        element.appendChild(textNode);
    },
    draw: function(month, year, calDiv, callback, isFieldMonth, fieldDay) {
        while (calDiv.hasChildNodes())
            calDiv.removeChild(calDiv.lastChild);
        var table   = CdrCalendar.addElement('table', calDiv);
        var caption = CdrCalendar.addElement('caption', table);
        var tbody   = CdrCalendar.addElement('tbody', table);
        var tr      = CdrCalendar.addElement('tr', tbody);
        var title   = CdrCalendar.months[month - 1] + ' ' + year;
        if (CdrCalendar.sticky == 2) {
            CdrCalendar.debugLog('sticky month=' + month + ' year=' + year);
            CdrCalendar.month = month;
            CdrCalendar.year  = year;
        }
        CdrCalendar.addTextNode(title, caption);
        for (var i = 0; i < 7; i++) {
            var th = CdrCalendar.addElement('th', tr);
            CdrCalendar.addTextNode(CdrCalendar.days[i], th);
        }
        var firstDay = new Date(year, month - 1, 1).getDay();
        var days = CdrCalendar.getDaysInMonth(month, year);
        tr = CdrCalendar.addElement('tr', tbody);
        for (var i = 0; i < firstDay; i++) {
            var td = CdrCalendar.addElement('td', tr);
            td.style.backgroundColor = '#f3f3f3';
        }
        var day = 1;
        for (var i = firstDay; day <= days; i++) {
            if (i % 7 == 0 && day != 1)
                tr = CdrCalendar.addElement('tr', tbody);
            var td = CdrCalendar.addElement('td', tr);
            var func = callback + '(' + year + ',' + month + ',' + day + ')';
            var href = 'javascript:void(' + func + ');';
            var link = CdrCalendar.addElement('a', td);
            link.setAttribute('href', href);
            link.style.textDecoration = "none";
            if (isFieldMonth && fieldDay == day)
                link.className = 'cdr-cur-day';
            CdrCalendar.addTextNode(day++, link);
        }

        // Draw blanks after end of month
        while (tr.childNodes.length < 7) {
            var td = CdrCalendar.addElement('td', tr);
            td.style.backgroundColor = '#f3f3f3';
        }

    },
    init: function() {
        CdrCalendar.makeDebugBox();
        var inputs = document.getElementsByTagName('input');
        for (var i = 0; i < inputs.length; i++) {
            var field = inputs[i];
            if (field.className.match(/CdrDateField/))
                CdrCalendar.addCalendar(field);
        }
    },
    makeDebugBox: function() {
        var form = undefined;
        if (document.forms)
            form = document.forms[0];
        if (form && form.debug && form.debug.value) {
            CdrCalendar.debugBox = document.createElement('textarea');
            CdrCalendar.debugBox.style.width = "600px";
            CdrCalendar.debugBox.style.height = "300px";
            CdrCalendar.debugBox.style.display = "none";
            document.forms[0].appendChild(CdrCalendar.debugBox);
        }
        else
            CdrCalendar.debugBox = undefined;
    },
    getFieldDate: function(field) {
        var match = field.value.match(/(\d{4})-(\d{2})-(\d{2})/);
        if (match)
            return new Date(match[1], match[2] - 1, match[3]);
        else
            return new Date();
    },

    Calendar: function(num, calBox, img) {
        this.num       = num;
        this.field     = CdrCalendar.fields[num];
        this.callback  = CdrCalendar.handleCalendarCallback(num);
        this.divId     = CdrCalendar.calMainIdBase + num;
        this.calBox    = calBox;
        this.img       = img;
        this.fieldDate = CdrCalendar.getFieldDate(this.field);
        this.month     = this.fieldDate.getMonth() + 1;
        this.year      = this.fieldDate.getFullYear();
    },

    findX: function(obj) {
        var x = 0;
        var o = obj;
        if (o.offsetParent) {
            while (o.offsetParent) {
                x += o.offsetLeft;
                o = o.offsetParent;
            }
        }
        else if (o.x)
            x = o.x;
        return x;
    },
    debugLog: function(what) {
        if (CdrCalendar.debugBox) {
            CdrCalendar.debugBox.style.display = 'block';
            CdrCalendar.debugBox.value += what + "\r\n";
        }
    },
    findY: function(obj) {
        var y = 0;
        var o = obj;
        if (o.offsetParent) {
            while (o.offsetParent) {
CdrCalendar.debugLog("o="+o+" o.nodeName="+o.nodeName+" offsetTop="+o.offsetTop);
// if (o.offsetTop + 0 < 300)
                y += o.offsetTop;
                o = o.offsetParent;
            }
            var n = obj.parentNode;
            while (n && n != document.body) {
CdrCalendar.debugLog("n="+n+" n.nodeName="+n.nodeName+" n.scrollTop="+n.scrollTop);
                if (n.scrollTop) {
// alert('scrollTop=' + n.scrollTop);
                    y -= n.scrollTop;
                }
                n = n.parentNode;
            }
        }
        else if (o.y)
            y = o.y;
        return y;
    },
    getViewportWidth: function() {
        if (window.innerWidth)
            return window.innerWidth;
        if (document.documentElement && document.documentElement.clientWidth)
            return document.documentElement.clientWidth;
        else
            return document.body.clientWidth;
    },
    getViewportHeight: function() {
        if (window.innerHeight)
            return window.innerHeight;
        if (document.documentElement && document.documentElement.clientHeight)
            return document.documentElement.clientHeight;
        else
            return document.body.clientHeight;
    },
    openCalendar: function(n) {
        var boxId     = CdrCalendar.calBoxIdBase + n;
        var calBox    = document.getElementById(boxId);
        var target    = window;
        var cal       = CdrCalendar.cals[n];
        CdrCalendar.debugLog('sticky=' + CdrCalendar.sticky + ' year=' +
                             CdrCalendar.year);
        if (CdrCalendar.sticky == 0) {
            var d     = CdrCalendar.getFieldDate(cal.field);
            cal.month = d.getMonth() + 1;
            cal.year  = d.getFullYear();
        }
        else if (CdrCalendar.sticky == 2 && CdrCalendar.year) {
            cal.month = CdrCalendar.month;
            cal.year  = CdrCalendar.year;
        }
        cal.draw();
        if (CdrCalendar.ie)
            target = document.body;
        calBox.style.display = 'block';
        CdrCalendar.addEvent(target, 'click', function() {
            CdrCalendar.dismissCalendar(n);
            return true;
        });
    },
    dismissCalendar: function(num) {
        var divId  = CdrCalendar.calBoxIdBase + num;
        var calDiv = document.getElementById(divId);
        calDiv.style.display = 'none';
    },
    prevMonth: function(num) {
        CdrCalendar.cals[num].drawPreviousMonth();
    },
    nextMonth: function(num) {
        CdrCalendar.cals[num].drawNextMonth();
    },
    prevYear: function(num) {
        CdrCalendar.cals[num].drawPreviousYear();
    },
    nextYear: function(num) {
        CdrCalendar.cals[num].drawNextYear();
    },
    handleCalendarCallback: function(num) {
        return "function(y, m, d) {\n" +
               "    var f = CdrCalendar.fields[" + num + "];\n" +
               "    var i = CdrCalendar.calBoxIdBase + " + num + ";\n" +
               "    var c = document.getElementById(i);\n" +
               "    f.value = CdrCalendar.makeIsoDate(y,m,d);\n" +
               "    if (f.onchange) f.onchange();\n" +
               "    c.style.display = 'none';\n" +
               "}\n";
    },
    stopPropagation: function(e) {
        if (!e) e = window.event;
        e.cancelBubble = true;
        if (e.stopPropagation) e.stopPropagation();
    }
};

CdrCalendar.Calendar.prototype = {
    draw: function() {
        var fieldDate  = CdrCalendar.getFieldDate(this.field);
        var fieldMonth = fieldDate.getMonth() + 1;
        var fieldYear  = fieldDate.getFullYear();
        var fieldDay   = fieldDate.getDate();
        var sameMonth  = this.month == fieldMonth && this.year == fieldYear;
        var calDiv     = document.getElementById(this.divId);
        CdrCalendar.draw(this.month, this.year, calDiv, this.callback,
                         sameMonth, fieldDay);
        this.adjustPosition();
    },
    adjustPosition: function() {
        var x        = CdrCalendar.findX(this.img) + 20;
        var y        = CdrCalendar.findY(this.img);
        if (y < 0)
            y = 0;
        if (x < 0)
            x = 0;
        this.calBox.style.position = 'absolute';
        this.calBox.style.left = x + 'px';
        this.calBox.style.top  = y + 'px';
    },
    drawDate: function(month, year) {
        this.month = month;
        this.year = year;
        this.draw();
    },
    drawPreviousMonth: function() {
        if (this.month == 1) {
            this.month = 12;
            this.year--;
        }
        else {
            this.month--;
        }
        this.draw();
    },
    drawNextMonth: function() {
        if (this.month == 12) {
            this.month = 1;
            this.year++;
        }
        else {
            this.month++;
        }
        this.draw();
    },
    drawPreviousYear: function() {
        this.year--;
        this.draw();
    },
    drawNextYear: function() {
        this.year++;
        this.draw();
    }
};

CdrCalendar.addEvent(window, 'load', CdrCalendar.init);
