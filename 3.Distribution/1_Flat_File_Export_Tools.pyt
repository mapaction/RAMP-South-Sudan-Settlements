import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "South Sudan Settlement Tools"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [ExtractSettlements]




class ExtractSettlements(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Extract Settlements Layer"
        self.description = "Extracts the settlements geodatabase into a single feature class."
        self.canRunInBackground = False


    primary_fields = ['SHAPE@','SETTLEMENT_NAME','STATE_NAME','COUNTY_NAME','PAYAM_NAME','BOMA_NAME','SRC_LATITUDE','SRC_LONGITUDE',
                            'FUNCTIONAL_CLASSIFICATION','TEMPORAL_CLASSIFICATION','VERIFICATION_REMARKS','VERIFIED','DATA_SOURCE','SOURCE_GUID','SRC_CONFIDENCE','VERIFIED_DATE','MA_VERIFIED','MA_REMARKS','OID@','SHAPE@XY']

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Use for testing :

        # https://desktop.arcgis.com/en/desktop/latest/analyze/creating-tools/defining-parameter-data-types-in-a-python-toolbox.htm
        params_list = []
        params_list.append(arcpy.Parameter(
        displayName="Workspace",
        name="workspace",
        datatype="DEWorkspace",
        parameterType="Optional",
        enabled=False,
        direction="Input" ))
        #valueAsText=default_workspace

        params_list.append(arcpy.Parameter(
        displayName="Primary Settlements", #1
        name="fc_primary_settlements",
        datatype="DEFeatureClass",
        parameterType="Required",
        direction="Input"))
        #     valueAsText = default_workspace + 'Primary_Settlements'

##        param_fieldmap = arcpy.Parameter(
##                            displayName="Primary Settlement Fields", #2
##                            name="primary_fieldmap",
##                          datatype="GPValueTable",
##                          parameterType="Optional",
##                          enabled=False,
##                          multiValue = False,
##                          direction="Input" )
##
##        param_fieldmap.columns = [["GPString","Settlement Field"], ["GPString","Input Field"]]
##        _param_fieldmap_values = []
##        for field_name in self.primary_fields:
##            if not "@" in field_name:
##                _param_fieldmap_values.append([field_name, None])
##                #param_fieldmap.addRow(field_name)
##        param_fieldmap.values = _param_fieldmap_values
##        params_list.append(param_fieldmap)
        params_list.append(arcpy.Parameter(
        displayName="Alternative Settlements", #2
        name="fc_alternative_settlements",
        datatype="DEFeatureClass",
        parameterType="Required",
        direction="Input"
        ))

        params_list.append(arcpy.Parameter(
        displayName="Output Settlements Layer",#3
        name="fc_output",
        datatype="DEFeatureClass",
        parameterType="Required",
        direction="Input"))

        cb_param = arcpy.Parameter(
        displayName="Initialise output dataset", #4
        name="b_truncate_output",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input")
        cb_param.value = False

        params_list.append(cb_param)
        return params_list

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        # If primary has been set, then update field map parameter
        if parameters[1].altered:
            parameters[2].enabled = True
            # Loop through fields on input table, and set as dropdown options (by type), on output field.
            #parameters[2].setErrorMessage("OLDNAME - " + parameters[2].name)
            #parameters[2].addTable(parameters[1].valueAsText)
        #parameters[3].setErrorMessage("NAME - " + parameters[2].name)
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
##        if parameters[1].altered:
##            parameters[2].addTable(parameters[1].valueAsText)
##        parameters[3].setErrorMessage("NAME - " + parameters[2].name)
        return

    def processPrimary(self):
        arcpy.AddMessage("Opening Primary Settlements layer : {0} ({1} Settlements)".format(self.fc_primary_settlements,self._primary_count))
            # Temp for dev
            #_count += 1
            #if (_count == 10):
            #    sys.exit()

            # Row fields
            # 0. Shape
            # 1. Settlement Name
            # 2. State Name
            # 3. County Name
            # 4. Payam Name
            # 5. Boma Name
            # 6-7 SRC_LAT SRC_LON
            # 8. Functional Class
            # 9. Temporal Class
            # 10. Src Verification Remarks
            # 11. Src Verified
            # 12. Data Source
            # 13. GUID (12)
            # 14. MA Score (13)
            # 15. Verified Date
            # 16. MA Verified
            # 17. MA Remarks
            # 1a. In cursor open new cursor on alternative settlements rows, sort by score (descending) (related SQL)
        alternative_fields = ['SETTLEMENT_NAME','DATA_SOURCE','SRC_CONFIDENCE']

        with arcpy.da.SearchCursor(self.fc_primary_settlements, self.primary_fields) as cursor:
            for primary_settlement in cursor:
                if primary_settlement[1] is None:
                    arcpy.AddWarning("No settlement name for input feature with ObjectID : {0}".format(primary_settlement[18]))
                    primary_settlement = cursor.next()
                # Extract Attributes from primary row:
                settlement_names = [primary_settlement[1].strip()]
                uc_settlement_names = [str(primary_settlement[1]).upper()]
                data_sources = [str(primary_settlement[12])]
                if primary_settlement[14] is not None:
                    sum_confidence_score = primary_settlement[14]
                else:
                    sum_confidence_score = 0
                if primary_settlement[13] is not None:
                    _primary_guid = primary_settlement[13]
                    _alt_query = """"PREFERRED_SETTLEMENT_ID" = '""" + _primary_guid + """'"""
                    with arcpy.da.SearchCursor(self.fc_alternative_settlements, alternative_fields, _alt_query,sql_clause=(None,'ORDER BY SRC_CONFIDENCE DESC')) as alt_cursor:
                        # TODO - Also populate other fields if they are missing from the primary, e.g. State, Payam etc..
                        for alternative_row in alt_cursor:
                            if alternative_row[1] not in data_sources:
                                data_sources.append(str(alternative_row[1]))
                            if alternative_row[0] is not None and str(alternative_row[0]).strip().upper() not in uc_settlement_names:
                                settlement_names.append(alternative_row[0].strip())
                                uc_settlement_names.append(str(alternative_row[0]).upper().strip())
                            if alternative_row[2] is not None:
                                sum_confidence_score += alternative_row[2]

                else:
                    arcpy.AddWarning("No SRC_GUID for input settlement with ObjectID : {0}".format(primary_settlement[18]))
                    _primary_guid = "" #"ObjectID-{0}".format(primary_settlement[18])
                # Save Output Row - All primary attributes, alternative names and datasources from alternative feature class.
                dn_row = self.output_rows.newRow()
                dn_row.shape = primary_settlement[0] #arcpy.Point(row[1][0],row[1][1]) #
                dn_row.setValue("name",settlement_names[0])
                dn_row.setValue("state_name",primary_settlement[2])
                dn_row.setValue("county",primary_settlement[3])
                dn_row.setValue("payam",primary_settlement[4])
                dn_row.setValue("boma",primary_settlement[5])
                dn_row.setValue("func_class",primary_settlement[8])
                dn_row.setValue("temp_class",primary_settlement[9])
                dn_row.setValue("src_lat",primary_settlement[6])
                dn_row.setValue("src_lon",primary_settlement[7])
                dn_row.setValue("src_verifd",primary_settlement[11])
                dn_row.setValue("src_v_rem",primary_settlement[10])
                dn_row.setValue("data_sources",', '.join(data_sources))
                dn_row.setValue("ma_verifd",primary_settlement[16])
                dn_row.setValue("ma_v_date",primary_settlement[15])
                dn_row.setValue("ma_score",sum_confidence_score)
                dn_row.setValue("src_guid",_primary_guid)
                # Alternative names
                if len(settlement_names) > 1:
                      for i in range(len(settlement_names[1:6])):
                        dn_row.setValue("alt_name"+ str(i+1),settlement_names[i+1])
                if len(settlement_names) > 4:
                    arcpy.AddWarning("More than 4 alternative names for : {0} ({1})".format(settlement_names[0],str(len(settlement_names))))
                self.output_rows.insertRow(dn_row)
                del dn_row
                arcpy.SetProgressorPosition()




    def setupProgress(self, parameters):
        """Sets up progress indicators"""
        arcpy.MakeTableView_management(self.fc_primary_settlements, "primaryTableView")
        self._primary_count = int(arcpy.GetCount_management("primaryTableView").getOutput(0))
        arcpy.Delete_management("primaryTableView")
        arcpy.SetProgressor("step",'Processing Settlements...',0,self._primary_count+1)

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Set instance properties from parameters :
        self.fc_primary_settlements = parameters[1].valueAsText
        self.fc_alternative_settlements = parameters[2].valueAsText
        self.fc_output_layer = parameters[3].valueAsText

        # TESTING:
        #dev_workspace = "C:/Users/andrew.kesterton/Dropbox/work/Mapaction/ss/Scripting-export/export_testing.gdb/"
        #self.fc_primary_settlements = dev_workspace + "Primary_Settlements"
        #self.fc_alternative_settlements = dev_workspace + "Alternative_Settlements"
        #self.fc_output_layer = dev_workspace + "settlements_denormalised"

        if parameters[4].value:
            arcpy.DeleteRows_management(self.fc_output_layer)
        self.setupProgress(parameters)

        # TODO Change to da.insertCursor (requires field names)
        self.output_rows = arcpy.InsertCursor(self.fc_output_layer)
        # Process Data:
        self.processPrimary()
        return




