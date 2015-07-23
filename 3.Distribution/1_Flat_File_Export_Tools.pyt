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
    alternative_fields = ['SETTLEMENT_NAME','DATA_SOURCE','SRC_CONFIDENCE']

    def getParameterInfo(self):
        """Define parameter definitions"""

        # https://desktop.arcgis.com/en/desktop/latest/analyze/creating-tools/defining-parameter-data-types-in-a-python-toolbox.htm
        params_list = []
        params_list.append(arcpy.Parameter(
        displayName="Primary Settlements", #0
        name="fc_primary_settlements",
        datatype="DEFeatureClass",
        parameterType="Required",
        direction="Input"))

        params_list.append(arcpy.Parameter(
        displayName="Alternative Settlements", #1
        name="fc_alternative_settlements",
        datatype=["DEFeatureClass","DETable"],
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

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[0].altered:
            # Check fields in Primary Feature Class
            primary_input_fields = [f.name for f in arcpy.ListFields(parameters[0].value)]
            primary_missing_fields = []
            for req_field in self.primary_fields:
                if req_field.find('@') == -1 and req_field not in primary_input_fields:   #not req_field.find('@') and
                    primary_missing_fields.append(req_field)
            if len(primary_missing_fields) >=1:
                parameters[0].setErrorMessage("Required field(s) missing: {0}".format(', '.join(primary_missing_fields)))

        if parameters[1].altered:
            # Check fields in Alternative Table
            alternative_input_fields = [f.name for f in arcpy.ListFields(parameters[1].value)]
            alternative_missing_fields = []
            for req_field in self.alternative_fields:
                if req_field.find('@') == -1 and req_field not in alternative_input_fields:
                    alternative_missing_fields.append(req_field)
            if len(alternative_missing_fields) > 0:
                parameters[1].setErrorMessage("Required field(s) missing: {0}".format(', '.join(alternative_missing_fields)))

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
                    with arcpy.da.SearchCursor(self.fc_alternative_settlements, self.alternative_fields, _alt_query,sql_clause=(None,'ORDER BY SRC_CONFIDENCE DESC')) as alt_cursor:
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
                      for i in range(len(settlement_names[1:5])):
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
        self.fc_primary_settlements = parameters[0].valueAsText
        self.fc_alternative_settlements = parameters[1].valueAsText
        self.fc_output_layer = parameters[2].valueAsText

        if parameters[3].value:
            arcpy.DeleteRows_management(self.fc_output_layer)
        self.setupProgress(parameters)

        # TODO Change to da.insertCursor (requires field names)
        self.output_rows = arcpy.InsertCursor(self.fc_output_layer)
        # Process Data:
        self.processPrimary()
        return




