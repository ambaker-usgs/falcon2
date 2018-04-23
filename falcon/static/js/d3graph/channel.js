function buildGraph()
{
    // Set the dimensions of the canvas / graph
    var margin = {top: 30, right: 20, bottom: 110, left: 70},
        width = 1200 - margin.left - margin.right,
        height = 740 - margin.top - margin.bottom;

    // Parse the date / time
    var parseDate = d3.time.format("%Y-%j").parse;

    // Set the ranges
    var x = d3.time.scale().range([0, width]);
    var y = d3.scale.linear().range([height, 0]);

    // Define the axes
    var xAxis = d3.svg.axis()
        .scale(x)
        .orient("bottom")
        //.ticks(10)
        .innerTickSize(-height)
        .tickPadding(10);

    var yAxis = d3.svg.axis()
        .scale(y)
        .orient("left")
        //.ticks(10)
        .innerTickSize(-width)
        .tickPadding(10);

    // Define the line
    var valueline = d3.svg.line()
        .x(function(d) { return x(d.date); })
        .y(function(d) { return y(d.value); });

    // Adds the svg canvas
    var svg = d3.select("body")
        .append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
        .append("g")
            .attr("transform",
                  "translate(" + margin.left + "," + margin.top + ")")
        //.call(d3.behavior.zoom().on("zoom", function () {svg.attr("transform", "translate(" + d3.event.translate + ")" + " scale(" + d3.event.scale + ")")}));

        svg.append("rect")
            .attr("width", width)
            .attr("height", height)
            .attr("fill", "#f2f2f2")
            .style("stroke", "black")
            .style("stroke-width", 1);


    // Get the data
    //d3.csv("data.csv", function(error, data) {
        //document.plot_data = [
        //{'id': 'Average', 'values': [{'date': '2017-345', 'value': 28.13}, {'date': '2017-346', 'value': 59.13}, {'date': '2017-347', 'value': 43.0}]},
        //{'id': 'High', 'values': [{'date': '2017-345', 'value': 32.13}, {'date': '2017-346', 'value': 63.13}, {'date': '2017-347', 'value': 45.0}]},
        //{'id': 'Low', 'values': [{'date': '2017-345', 'value': 26.13}, {'date': '2017-346', 'value': 55.13}, {'date': '2017-347', 'value': 40.0}]}
        //];

        document.plot_data.data.map(function(item) {
            item.values.map(function(d) {
                    d.date = parseDate(d.date);
                    //d.value = +d.value;
            });
        });

        // Scale the range of the data
        x.domain(d3.extent(document.plot_data.data[0].values, function(d) { return d.date; }));
        y.domain([
         d3.min(document.plot_data.data, function(d) { return d3.min(d.values, function(v) { return v.value; }); }),
         d3.max(document.plot_data.data, function(d) { return d3.max(d.values, function(v) { return v.value; }); })
        ]);

        var color = d3.scale.category10();

        document.plot_data.data.forEach(function(d) {
            // Add the valueline path.
            svg.append("path")
                .attr("class", "line")
                .attr("d", valueline(d.values))
                .style("stroke", function() { return d.color = color(d.id); })
                .attr("data-legend", d.id);
        });

        // Add the X Axis
        svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")
            .style("font", "1em")
            .call(xAxis.tickFormat(d3.time.format("%Y-%j")))
            .selectAll("text")
                .style("text-anchor", "end")
                .attr("dx", "-.8em")
                .attr("dy", ".15em")
                .attr("transform", function(d) { return "rotate(-65)" });

        // Add the Y Axis
        svg.append("g")
            .attr("class", "y axis")
            .call(yAxis)

        // Y axis label
        svg.append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 0-50)
            .attr("x", 0-(height/2))
            .style("text-anchor", "middle")
            .text(document.plot_data.units);

        // X axis label
        svg.append("text")
            .attr("x", width/2)
            .attr("y", height+100)
            .style("text-anchor", "middle")
            .text('Date');

        var legendx = width-150;
        var legendy = height - 70;
        svg.append("g")
            .attr("class","legend")
            .attr("transform","translate(" + legendx + "," + legendy + ")")
            .attr("fill", "white")
            .style("font-size","1em")
            .call(d3.legend);
        d3.selectAll(".legend-items text").style("fill", "black");
    //});
}
