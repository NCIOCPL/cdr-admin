/*
 * $Id$
 *
 * Client-side code for displaying popup descriptions of indicators
 * and reforms used in the simulation.  Derived from the HTML pages
 * provided by the designer for the project.  The code has been
 * rewritten to encapsulate this functionality inside a single
 * namespace, so we don't run the risk of stepping on global
 * variables in other packages (or in our own code, for that matter).
 *
 * See the comment in Indicators.cs concerning what appears to be
 * redundant layers of table-markup around the strings being displayed
 * in the popup windows.
 *
 * If you decide that the popups are appearing too quickly (or not
 * quickly enough), you can adjust CdrTooltip.delay below.  In fact,
 * there are a bunch of things you can tweak, right under the comment
 * that says "Settings to control tooltip behavior ...."
 */
CdrTooltip = new Object();

// Browser capability detection; project only supports IE5+ and NS6+/Mozilla.
CdrTooltip.dom = document.getElementById ? true : false;
CdrTooltip.ns6 = navigator.userAgent.indexOf("Gecko") > -1 && CdrTooltip.dom;
CdrTooltip.ie5 = navigator.userAgent.indexOf("MSIE") > -1 && CdrTooltip.dom;
CdrTooltip.supported = CdrTooltip.ns6 || CdrTooltip.ie5;

// Settings to control tooltip behavior, appearance.
CdrTooltip.followMouse = true;
CdrTooltip.width       = 500;
CdrTooltip.offX        = 20;
CdrTooltip.offY        = 12;
CdrTooltip.fontFamily  = "Verdana, Arial, Helvetica, sans-serif";
CdrTooltip.fontSize    = "7pt";
CdrTooltip.fontColor   = "#333377";
CdrTooltip.bgColor     = "#FFFFFF";
CdrTooltip.borderColor = "#003366";
CdrTooltip.borderWidth = 1;
CdrTooltip.borderStyle = "solid";
CdrTooltip.padding     = 0;
CdrTooltip.delay       = 100;

// Tooltip content collection (populated at runtime).
CdrTooltip.content = new Object();

// This is where the tip goes in the page and how it is displayed.
CdrTooltip.div = null;
CdrTooltip.css = null;

// Mouse coordinates captured when event occurs.
CdrTooltip.mouseX = 0;
CdrTooltip.mouseY = 0;

// Timeout control.
CdrTooltip.timeout1 = null;
CdrTooltip.timeout2 = null;

// State variable.
CdrTooltip.tipOn = false;

// Stock strings for tooltip markup.
CdrTooltip.startStr = '<table cellspacing="0" cellpadding="0" width="'
                   + CdrTooltip.width
                   + '"><tr><td align="center" width="100%">';
CdrTooltip.endStr = '</td></tr></table>';

/*
 * doTooltip()
 *
 *   assembles content for tooltip and writes it to tipDiv.
 *
 */
CdrTooltip.doTooltip = function(evt, key) {
    if (!CdrTooltip.div) return;
    // CdrTooltip.width = key.substring(0, 3) == "ref" ? 360 : 160;
    if (CdrTooltip.timeout1) clearTimeout(CdrTooltip.timeout1);
    if (CdrTooltip.timeout2) clearTimeout(CdrTooltip.timeout2);
    CdrTooltip.tipOn = true;
    var tip = '<table cellspacing="0" cellpadding="0" width="'
            + CdrTooltip.width
            + '"><tr><td align="center" width="100%">'
            + '<span style="font-family:' + CdrTooltip.fontFamily
            + '; font-size:' + CdrTooltip.fontSize
            + '; color:' + CdrTooltip.fontColor + ';">'
            + CdrTooltip.content[key] + '</span></td></tr></table>';
    CdrTooltip.css.backgroundColor = CdrTooltip.bgColor;
    CdrTooltip.css.width           = CdrTooltip.width + "px";
    CdrTooltip.div.innerHTML = tip;
    if (!CdrTooltip.followMouse)
        CdrTooltip.positionTip(evt);
    else {
        var action = "CdrTooltip.css.visibility='visible'";
        CdrTooltip.timeout1 = setTimeout(action, CdrTooltip.delay);
    }
}

/*
 * Separate function for determining where the popup window should 
 * appear.
 */
CdrTooltip.positionTip = function(evt) {
    if (!CdrTooltip.supported) return;
    if (!CdrTooltip.followMouse) {
        if (CdrTooltip.ns6) {
            CdrTooltip.mouseX = evt.pageX;
            CdrTooltip.mouseY = evt.pageY;
        }
        else {
            CdrTooltip.mouseX = window.event.clientX
                              + document.body.scrollLeft;
            CdrTooltip.mouseY = window.event.clientY + document.body.scrollTop;
        }
    }
    // Calculate some working window and tooltip size values.
    var winWd, winHt, tpWd, tpHt;
    if (CdrTooltip.ie5) {
        tpWd  = CdrTooltip.div.clientWidth;
        tpHt  = CdrTooltip.div.clientHeight;
        winWd = document.body.clientWidth + document.body.scrollLeft;
        winHt = document.body.clientHeight + document.body.scrollTop;
    }
    else {
        tpWd  = CdrTooltip.div.offsetWidth;
        tpHt  = CdrTooltip.div.offsetHeight;
        winWd = window.innerWidth - 20 + window.pageXOffset;
        winHt = window.innerHeight - 20 + window.pageYOffset;
    }
    
    // check mouse position against tip and window dimensions
    // and position the tooltip
    var left, top;
    if (CdrTooltip.mouseX + CdrTooltip.offX + tpWd > winWd)
        left = CdrTooltip.mouseX - (tpWd + CdrTooltip.offX);
    else
        left = CdrTooltip.mouseX + CdrTooltip.offX;
    if (CdrTooltip.mouseY + CdrTooltip.offY + tpHt > winHt)
        top  = winHt - (tpHt + CdrTooltip.offY);
    else
        top  = CdrTooltip.mouseY + CdrTooltip.offY;
    CdrTooltip.css.left = left + "px";
    CdrTooltip.css.top  = top  + "px";
    if (!CdrTooltip.followMouse) {
        var action = "CdrTooltip.css.visibility='visible'";
        CdrTooltip.timeout1 = setTimeout(action, CdrTooltip.delay);
    }
}

/*
 * This is what we do when the mouse leaves the area which triggers
 * the popup.
 */
CdrTooltip.hideTip = function() {
    if (!CdrTooltip.div) return;
    var action = "CdrTooltip.css.visibility='hidden'";
    CdrTooltip.timeout2 = setTimeout(action, CdrTooltip.delay);
    CdrTooltip.tipOn = false;
}

// Initialize CdrTooltip.div and CdrTooltip.css.
window.onload = function() {

    // We only support IE5+ and NS6+
    if (!CdrTooltip.supported) return;
    CdrTooltip.div                 = document.getElementById('tipDiv');
    CdrTooltip.css                 = CdrTooltip.div.style;
    CdrTooltip.css.width           = CdrTooltip.width + "px";
    CdrTooltip.css.fontFamily      = CdrTooltip.fontFamily;
    CdrTooltip.css.fontSize        = CdrTooltip.fontSize;
    CdrTooltip.css.color           = CdrTooltip.fontColor;
    CdrTooltip.css.backgroundColor = CdrTooltip.bgColor;
    CdrTooltip.css.borderColor     = CdrTooltip.borderColor;
    CdrTooltip.css.borderWidth     = CdrTooltip.borderWidth + "px";
    CdrTooltip.css.padding         = CdrTooltip.padding + "px";
    CdrTooltip.css.borderStyle     = CdrTooltip.borderStyle;
    if (CdrTooltip.div && CdrTooltip.followMouse) {
        document.onmousemove = function(evt) {
            if (CdrTooltip.ns6) {
                CdrTooltip.mouseX = evt.pageX;
                CdrTooltip.mouseY = evt.pageY;
            }
            else {
                CdrTooltip.mouseX = window.event.clientX
                                  + document.body.scrollLeft;
                CdrTooltip.mouseY = window.event.clientY
                                  + document.body.scrollTop;
            }
            if (CdrTooltip.tipOn) CdrTooltip.positionTip(evt);
        }
    }
}
