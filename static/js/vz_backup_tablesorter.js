$(document).ready(function() {
    $('#vz_backup_ba_table thead th.sorter').each(function(){
        str = $(this).html();
        $(this).html('<a href="#">'+str+"</a>");
    });
    $('#vz_backup_ba_table').tablesorter(
        {
            headers: { 5: {sorter: false} },
            cssDesc: 'sorted descending',
            cssAsc: 'sorted ascending',
            cssHeader: '',
        }
    );
    $('#vz_backup_ba_table').bind('sortEnd', function(){
        $('#vz_backup_ba_table tbody tr').removeClass('row1 row2');
        $('#vz_backup_ba_table tbody tr:odd').addClass('row2');
        $('#vz_backup_ba_table tbody tr:even').addClass('row1');
    });
});