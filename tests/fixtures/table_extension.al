tableextension 50100 "Customer Ext" extends Customer
{
    fields
    {
        field(50100; "Loyalty Level"; Enum "Customer Loyalty")
        {
            Caption = 'Loyalty Level';
            DataClassification = CustomerContent;

            trigger OnValidate()
            begin
                if "Loyalty Level" = "Loyalty Level"::Gold then
                    Message('This customer has achieved Gold status!');
            end;
        }
        field(50101; "Address Count"; Integer)
        {
            Caption = 'Address Count';
            FieldClass = FlowField;
            CalcFormula = count("Customer Address" where("Customer No." = field("No.")));
            Editable = false;
        }
    }
}
