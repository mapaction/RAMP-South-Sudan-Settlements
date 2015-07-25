import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "CSDS Maintenance Tools"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [PCode]


class PCode(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Generate P-Codes"
        self.description = "Generates P-Codes for Settlements based on input grid(s)."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = []

        params.append(arcpy.Parameter(
        displayName="Settlements Layer", #0
        name="fc_primary_settlements",
        datatype="DEFeatureClass",
        parameterType="Required",
        direction="Input"))

        field_param = arcpy.Parameter(
        displayName="P-Code Field", #0
        name="field_p_code",
        datatype="Field",
        parameterType="Required",
        direction="Input",
        )
        field_param.value = "P_CODE"
        field_param.filter.list = ['Text']
        field_param.parameterDependencies = ["fc_primary_settlements"]
        params.append(field_param)

        params.append(arcpy.Parameter(
        displayName="P-Code Grid", #0
        name="fc_p_code_grid",
        datatype="DEFeatureClass",
        parameterType="Required",
        direction="Input"))

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def updatePCodes(self):
        """Update blank P-Codes based on the grid system"""
        # Try cursor first otherwise go with spatial join (on feature layer created where P-code is null)
        grid_fields = ["SHAPE@","GRID"]
        settlement_fields = ["SHAPE@"]
        #settlement_fields.append(self.field_p_code)
        cnt_total_settlements = 0
        arcpy.MakeFeatureLayer_management(self.fc_settlements_layer, "settlements_layer")

        # Open search cursor on grid.
        with arcpy.da.SearchCursor(self.fc_p_code_grid, grid_fields) as grid_cursor:
            for grid_square in grid_cursor:
                s_grid_geometry = grid_square[0]
                # Select max P-code value from settlements
                max_code = 0
                # Select Settlements in Grid.
                # http://gis.stackexchange.com/questions/27350/does-arcpy-have-a-spatial-search-function-for-geometry?rq=1
                arcpy.SelectLayerByLocation_management("settlements_layer","INTERSECT",s_grid_geometry)
        # Open update cursor on
                with arcpy.da.UpdateCursor("settlements_layer", settlement_fields) as settlement_cursor:
                    for settlement in settlement_cursor:
                        max_code = max_code + 1
                        #settlement[1] = grid_cursor[1] + str(max_code)
                        #settlement_cursor.updateRow(settlement)
                if (max_code > 0):
                    cnt_total_settlements = cnt_total_settlements + max_code
                    arcpy.AddMessage("Grid {0} contains {1} settlements".format(grid_square[1],str(max_code)))
        arcpy.AddMessage("Total Settlements : {0}".format(str(cnt_total_settlements)))

    def execute(self, parameters, messages):
        """The source code of the tool."""
        self.fc_settlements_layer = parameters[0].valueAsText
        self.field_p_code =parameters[1].valueAsText
        self.fc_p_code_grid = parameters[2].valueAsText

        self.updatePCodes()

        return
