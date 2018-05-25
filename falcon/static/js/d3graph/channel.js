function buildGraph()
{
    // Base width and height of entire graph including axis, labels, legend
    var svgWidth = 1200;
    var svgHeight = 740;

    // Margins for data plot part of graph
    var margin = {top: 40, right: 20, bottom: 130, left: 70};

    // Area for data plot part of graph
    width = svgWidth - margin.left - margin.right,
    height = svgHeight - margin.top - margin.bottom;

    // Legend location and size
    var legend_width = 400;
    var legend_height = 50;
    var legendx = svgWidth - legend_width - margin.left - margin.right;
    var legendy = 0;
    // Function to Parse the date / time
    var parseDate = d3.timeParse("%Y-%m-%d");

    // Go through data and parse dates
    document.plot_data.data.map(function(item) {
        item.values.map(function(d) {
                d.date = parseDate(d.date);
        });
    });

    // Create X scale, both current and initial
    var Xdomain = [];
    if(document.plot_data.startdate)
        Xdomain = [parseDate(document.plot_data.startdate), parseDate(document.plot_data.enddate)];
    else
        Xdomain = d3.extent(document.plot_data.data[0].values, function(d) { return d.date; });
    var xScale = d3.scaleTime()
        .range([0, width])
        .domain(Xdomain);
    var xScale0 = d3.scaleTime()
        .range([0, width])
        .domain(Xdomain);

    // Create Y scale, both current and initial. Use plot data to get ymin and ymax with 2% margin from edge of graph initially
    var ymin = document.plot_data.ymin ? document.plot_data.ymin : d3.min(document.plot_data.data, function(d) { return d3.min(d.values, function(v) { return v.value - (v.value * 0.02); }); });
    var ymax = document.plot_data.ymax ? document.plot_data.ymax : d3.max(document.plot_data.data, function(d) { return d3.max(d.values, function(v) { return v.value + (v.value * 0.02); }); });
    if(!document.plot_data.ymin || !document.plot_data.ymax)
    {
        document.plot_data.ymin = ymin
        document.plot_data.ymax = ymax
    }
    if(ymin == 0 && ymax == 0)
    {
        ymin = -1.0;
        ymax = 1.0;
    }
    var yScale = d3.scaleLinear()
        .range([height, 0])
        .domain([ymin, ymax]);
    var yScale0 = d3.scaleLinear()
        .range([height, 0])
        .domain([ymin, ymax]);

    // Create X axis
    var xAxis = d3.axisBottom(xScale)
        .tickFormat(d3.timeFormat("%d-%b-%Y"))
        .tickPadding(10);

    var tdiff = Xdomain[1] - Xdomain[0];
    if(tdiff > 182*24*60*60*1000)
        xAxis.tickFormat(d3.timeFormat("%b-%Y"));

    // Create Y axis
    var yAxis = d3.axisLeft(yScale)
        .tickPadding(10);

    // Define zoom function
    var zoom = d3.zoom()
        .scaleExtent([1, 50])
        .translateExtent([[0, 0], [width, height]])
        .extent([[0, 0], [width, height]])
        .on("zoom", updateZoom);

    // This function creates the plot lines for graph passing in data
    var plotLine = d3.line()
        .x(function(d) { return xScale(d.date); })
        .y(function(d) { return yScale(d.value); });

    // Create the svg canvas
    var svg = d3.select("#graph").append("svg")
        .attr("id", "svggraph")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    // Create the clip region so that data does not plot outside plot area, css uses this
    svg.append("defs").append("clipPath")
        .attr("id", "clip")
       .append("rect")
        .attr("width", width)
        .attr("height", height);

    // create zoom portal in background and set mousemove and mouseup events on this object
    var zoomrect = svg.append("rect")
        .attr("class", "zoom")
        .attr("width", width)
        .attr("height", height)
        // On mouse down process the event
        .on("mousedown", function() {
            var e = this,
            origin = d3.mouse(e),
            rect = svg.append("rect").attr("class", "zoom");
            d3.select("#graph").classed("noselect", true);
            origin[0] = Math.max(0, Math.min(width, origin[0]));
            origin[1] = Math.max(0, Math.min(height, origin[1]));
            // Set action for mouse event
            d3.select(window)
                // On mousemove display a selection rect
                .on("mousemove.zoomRect", function() {
                     var m = d3.mouse(e);
                     m[0] = Math.max(0, Math.min(width, m[0]));
                     m[1] = Math.max(0, Math.min(height, m[1]));
                     rect.attr("x", Math.min(origin[0], m[0]))
                     .attr("y", Math.min(origin[1], m[1]))
                     .attr("width", Math.abs(m[0] - origin[0]))
                     .attr("height", Math.abs(m[1] - origin[1]));
                })
                // On mouse up zoom to that rect
                .on("mouseup.zoomRect", function() {
                    d3.select(window).on("mousemove.zoomRect", null).on("mouseup.zoomRect", null);
                    d3.select("#graph").classed("noselect", false);
                    var m = d3.mouse(e);
                    m[0] = Math.max(0, Math.min(width, m[0]));
                    m[1] = Math.max(0, Math.min(height, m[1]));
                    // Translate screen coordinates into plotting coordinates using the scales
                    if (m[0] !== origin[0] && m[1] !== origin[1]) {
                        xScale.domain([origin[0], m[0]].map(xScale.invert).sort(sortByDateAscending));
                        yScale.domain([origin[1], m[1]].map(yScale.invert).sort());
                    }
                    rect.remove();
                    updateZoom()
                }, true);
            // The event stops here
            d3.event.stopPropagation();
            })

    // Add Y gridlines
    var gridY = svg.append("g")
        .attr("class", "grid")
        .call(d3.axisLeft(yScale)
            .tickSize(-width)
            .tickFormat(""));

    // Add X gridlines
    var gridX = svg.append("g")
        .attr("class", "grid")
        .call(d3.axisBottom(xScale)
        .tickSize(height)
        .tickFormat(""));

    // Add legend
    svg.append("rect")
        .attr("width", legend_width)
        .attr("height", legend_height)
        .attr("class","legend")
        .attr("transform","translate(" + legendx + "," + legendy + ")")
        .attr("fill", "none")
        .style("font-size","1em")
        .style("stroke", "black")
        .style("stroke-width", 1);

    // Set color mapping for plot lines
    var color = d3.scaleOrdinal(d3.schemeCategory10);

    // Create the plot lines, looping through each data set
    var plots = [];
    document.plot_data.data.forEach(function(d, i) {
        plots.push(svg.append("path")
                      .attr("class", "line")  // This formats lines
                      .attr("d", plotLine(d.values))  // This creates plot data
                      .style("stroke", function() { return d.color = color(d.id); }))  // This sets color
        // Build the legend line/text for each data set
        currentx = 20 + (i * 117);
        svg.append("text")
            .attr("x", legendx + currentx + 30)
            .attr("y", legendy + legend_height/2 + 7)
            .attr("class", "legend")
            .style("fill", function() {return d.color = color(d.id)})
            .text(d.id);
        svg.append("line")
            .attr("x1", legendx + currentx)
            .attr("y1", legendy + legend_height/2)
            .attr("x2", legendx + currentx + 20)
            .attr("y2", legendy + legend_height/2)
            .style("stroke", function() {return d.color = color(d.id)});
    });

    // Add the X Axis
    var gX = svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .style("font", "1em")
        .call(xAxis)
        .selectAll("text")
            .style("text-anchor", "end")
            .attr("dx", "-.8em")
            .attr("dy", ".15em")
            .attr("transform", "rotate(-65)");

    // Add the Y Axis
    var gY = svg.append("g")
        .attr("class", "axis axis--y")
        .call(yAxis)

    // Y axis label
    svg.append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 0-55)
        .attr("x", 0-(height/2))
        .style("text-anchor", "middle")
        .text(document.plot_data.units);

    // X axis label
    svg.append("text")
        .attr("x", width/2)
        .attr("y", height+120)
        .style("text-anchor", "middle")
        .text('Date');

    // Title
    svg.append("text")
        .attr("class", "graphtitle")
        .attr("x", width/2)
        .attr("y", -25)
        .style("text-anchor", "middle")
        .text(document.plot_data.network + "_" + document.plot_data.station + " " + document.plot_data.channel + " (" + document.plot_data.description + ")");

    // No data message
    if(document.plot_data.data[0].values.length == 0)
    {
        svg.append("text")
            .attr("class", "graphtitle")
            .attr("x", width/2)
            .attr("y", height/2)
            .style("text-anchor", "middle")
            .text("No Data");
    }

    // This is the heart of the zoom
    function updateZoom() {

        // Update the x and y axis and tick labels

        // Set the x axis tick label format
        tdiff = Math.abs(xScale.domain()[1] - xScale.domain()[0]);
        if(tdiff > 182*24*60*60*1000)
            xAxis.tickFormat(d3.timeFormat("%b-%Y"));
        else
            xAxis.tickFormat(d3.timeFormat("%d-%b-%Y"));

        // Actually remove and redraw x axis
        gX.remove();
        gX = svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .style("font", "1em")
        .call(xAxis.scale(xScale))
        .selectAll("text")
            .style("text-anchor", "end")
            .attr("dx", "-.8em")
            .attr("dy", ".15em")
            .attr("transform", "rotate(-65)");

        gY.call(yAxis.scale(yScale));

        // Update the grid in the plot area
        gridX.call(d3.axisBottom(xScale)
            .tickSize(height)
            .tickFormat(""));
        gridY.call(d3.axisLeft(yScale)
            .tickSize(-width)
            .tickFormat(""));

        // Redraw the data plot lines
        plots.forEach(function(d, i) {
            d.attr("d", plotLine(document.plot_data.data[i].values))
        });
    }
}

// Set up the user scale inpout dialog
scaledialog = $("#userScale").dialog({
    autoOpen: false,
    height: 320,
    width: 400,
    modal: true,
    buttons: {
    "Update": function() {$('#user_scale_submit').click()},
    "Cancel": function() {scaledialog.dialog("close");}
    },
});

// Load the user scaling input form
function userScaling()
{
    $('#id_startdate').datepicker({dateFormat: "yy-mm-dd"}).val(document.plot_data.startdate);
    $('#id_enddate').datepicker({dateFormat: "yy-mm-dd"}).val(document.plot_data.enddate);
    $('#id_ymin').val(document.plot_data.ymin);
    $('#id_ymax').val(document.plot_data.ymax);
    $('#userScaleForm input:text').css('margin-left', '10px');
    scaledialog.dialog( "open" );
}

// If autoscale selected then disable ymin/ymax inputs
function yAutoScale(checkobj)
{
    var obj = $(checkobj);
    if(obj.is(':checked'))
    {
        $("[id^=id_ym]").attr("disabled", "disabled");
    }
    else
    {
        $("[id^=id_ym]").removeAttr("disabled", "disabled");
    }
}

// Export the graph to a png
function exportGraph()
{
    saveSvgAsPng(document.getElementById("svggraph"), document.plot_data.network + "_" + document.plot_data.station + "_" + document.plot_data.channel + ".png", { backgroundColor: 'white'});
}

// Sort algorithm for dates
function sortByDateAscending(a, b) {
    // Dates will be cast to numbers automagically:
    return a.date - b.date;
}
