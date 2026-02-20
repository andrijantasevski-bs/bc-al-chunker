pageextension 50100 "Customer Card Ext" extends "Customer Card"
{
    layout
    {
        addlast(General)
        {
            field("Loyalty Level"; Rec."Loyalty Level")
            {
                ApplicationArea = All;
                ToolTip = 'Specifies the loyalty level of the customer.';
            }
        }
    }

    actions
    {
        addlast(Processing)
        {
            action(ViewAddresses)
            {
                ApplicationArea = All;
                Caption = 'View Addresses';
                RunObject = page "Customer Address List";
                RunPageLink = "Customer No." = field("No.");
            }
        }
    }
}
