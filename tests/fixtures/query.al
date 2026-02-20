query 50100 "Customer Address Query"
{
    Caption = 'Customer Address Query';
    QueryType = Normal;

    elements
    {
        dataitem(Customer; Customer)
        {
            column(CustomerNo; "No.")
            {
            }
            column(CustomerName; Name)
            {
            }
            dataitem(Address; "Customer Address")
            {
                DataItemLink = "Customer No." = Customer."No.";
                SqlJoinType = InnerJoin;

                column(AddressLine; "Address Line 1")
                {
                }
                column(City; City)
                {
                }
                column(IsValidated; "Is Validated")
                {
                }
            }
        }
    }
}
