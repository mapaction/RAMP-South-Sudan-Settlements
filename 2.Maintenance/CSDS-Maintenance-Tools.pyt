import arcpy, os
## Tool to apply P-Codes based on one input dataset.
## Created by Mapaction


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

    NUMBER_OF_DIGITS = 4 # Number of digits for P-Code [XXnnnn] where XX is the grid identifier, and nnnn are the digits.
    SEPARATOR = "-" # Separator between 'grid' identifier and code, could be set to an empty string ("").
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
        direction="Input"
        )

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
        if parameters[0].altered:
            # Check whether feature class has a P-Code field and set parameter 1 accordingly.
            settlement_fields = [f.name for f in arcpy.ListFields(parameters[0].value)]
            if "P_CODE" in settlement_fields and not parameters[1].altered:
                parameters[1].value = "P_CODE"  # This doesn't seem to validate, maybe better for user to select manually. Or change to a value list?

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def getWorkspace(self,feature_class):
        '''Return the Geodatabase path from the input table or feature class.
        :param input_table: path to the input table or feature class
        '''
        workspace = os.path.dirname(feature_class)
        if [any(ext) for ext in ('.gdb', '.mdb', '.sde') if ext in os.path.splitext(workspace)]:
            return workspace
        else:
            return os.path.dirname(workspace)

    def getNextCode(self, prefix):
        """Returns the next value for the P-codes in the settlements layer based on the given prefix, after searching existing values. Assumes codes are [prefix]nnnn"""
        max_p_query = arcpy.AddFieldDelimiters(self.fc_settlements_layer, self.field_p_code) + " like '" + prefix + "%'"
        next_code = 1

        with arcpy.da.SearchCursor(self.fc_settlements_layer, [self.field_p_code], max_p_query,sql_clause=(None,'ORDER BY ' + self.field_p_code + ' DESC')) as p_code_cursor:
            for p_code in p_code_cursor:
                if int(p_code[0][len(prefix)+len(self.SEPARATOR):]) > next_code:
                    next_code = int(p_code[0][len(prefix)+len(self.SEPARATOR):]) + 1

        # Check whether we are running out of P-Codes
        # Raise 10 to the precision of the code to find the maximum value+1.
        if next_code > 10**self.NUMBER_OF_DIGITS-100:
            arcpy.AddWarning("Running out of P-Code values for grid {0}, only 99 P-Codes left when using {1} digits.  Consider increasing the number of digits (will require manual update of existing P-Codes).".format(prefix, self.NUMBER_OF_DIGITS))
        if next_code == 10**self.NUMBER_OF_DIGITS:
            arcpy.AddError("No P-Code values left for grid {0} as maximum number of settlements coded already ({1}). Increase the number of digits or grid resolution to continue.".format(prefix,(next_code-1)))
            raise Exception("P-Code Sequence Exhausted for Grid {0}".format(prefix))
        return next_code

    def updatePCodes(self):
        """Update blank P-Codes based on the grid system"""

        grid_fields = ["SHAPE@","GRID"]  # TODO make the polygon ID user selectable
        settlement_fields = ["SHAPE@XY"]
        settlement_fields.append(self.field_p_code)

        # Open search cursor on grid.
        with arcpy.da.SearchCursor(self.fc_p_code_grid, grid_fields) as grid_cursor:
            for grid_square in grid_cursor:
                s_grid_geometry = grid_square[0]
                # Select Settlements in Grid.
                arcpy.SelectLayerByLocation_management("settlements_layer","INTERSECT",s_grid_geometry)
                cnt_selected = arcpy.GetCount_management("settlements_layer")
                if cnt_selected > 0:
                    # Select max P-code value from settlements
                    next_code = self.getNextCode(grid_cursor[1])
                    # Open update cursor on Settlement Layer
                    with arcpy.da.UpdateCursor("settlements_layer", settlement_fields) as settlement_cursor:
                        for settlement in settlement_cursor:
                            settlement[1] = grid_cursor[1] + self.SEPARATOR + str(next_code).zfill(self.NUMBER_OF_DIGITS)
                            settlement_cursor.updateRow(settlement)
                            next_code = next_code + 1
                            arcpy.SetProgressorPosition()

                            # Check we haven't run out of P-Codes
                            if next_code == 10**self.NUMBER_OF_DIGITS:
                                arcpy.AddError("No P-Code values left for grid {0} as maximum number of settlements coded already ({1}). Increase the number of digits or alter grid resolution to continue.".format(grid_cursor[1],(next_code-1)))
                                raise Exception("P-Code Sequence Exhausted for Grid {0}".format(grid_cursor[1]))
        arcpy.SetProgressorLabel("Saving changes...")

    def execute(self, parameters, messages):
        """The source code of the tool."""
        self.fc_settlements_layer = parameters[0].valueAsText
        self.field_p_code =parameters[1].valueAsText
        self.fc_p_code_grid = parameters[2].valueAsText

        # Create feature layer for settlements that need a P Code.
        arcpy.MakeFeatureLayer_management(self.fc_settlements_layer, "settlements_layer",arcpy.AddFieldDelimiters(self.fc_settlements_layer, self.field_p_code) + " is null or " + arcpy.AddFieldDelimiters(self.fc_settlements_layer, self.field_p_code) + "= ''")
        # Setup a progress bar based on total number of blank settlements
        _empty_count = int(arcpy.GetCount_management("settlements_layer").getOutput(0))
        if _empty_count == 0:
            # No settlements without a code so do nothing and return.
            arcpy.AddWarning("No settlements without a P-Code.")
        else:
            arcpy.SetProgressor("step",'Calculating P-Codes...',0,_empty_count+1)
            arcpy.AddMessage("Calculating P-Codes for {0} settlements".format(_empty_count))
            # Start edit session and process P-Codes
            with arcpy.da.Editor(self.getWorkspace(self.fc_settlements_layer)) as edit:
                self.updatePCodes()

        return
